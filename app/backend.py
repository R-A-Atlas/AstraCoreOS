from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from app.command_center import default_command_center_state
from app.config import AppConfig
from app.capture_studio import CaptureStudio
from app.intel_runner import IntelRunner
from app.notifications import notification_channels
from app.operator_agent import OperatorAgent
from app.pine_generator import PineStrategyGenerator
from app.skills_registry import skill_catalog
from app.tradingview import TradingViewBridge


ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "web"
OUTPUTS = ROOT / "workspace" / "outputs"
CAPTURES = ROOT / "workspace" / "captures"
OUTPUTS.mkdir(parents=True, exist_ok=True)
CAPTURES.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="AstraCore OS", version="0.1.0")
config = AppConfig(ROOT)
agent = OperatorAgent(ROOT)
intel_runner = IntelRunner()
tradingview_bridge = TradingViewBridge(ROOT)
capture_studio = CaptureStudio(ROOT)
pine_generator = PineStrategyGenerator(ROOT)

app.mount("/static", StaticFiles(directory=WEB), name="static")
app.mount("/outputs", StaticFiles(directory=OUTPUTS), name="outputs")
app.mount("/captures", StaticFiles(directory=CAPTURES), name="captures")


class OperatorRequest(BaseModel):
    directive: str = Field(..., min_length=1, max_length=4000)
    deep_research: bool = False


class IntelRunRequest(BaseModel):
    skill_id: str = Field(..., min_length=1, max_length=100)
    directive: str = Field("", max_length=4000)


class PineStrategyRequest(BaseModel):
    name: str = Field("AstraCore Scalp Assist", max_length=100)
    notes: str = Field("", max_length=12000)


@app.get("/")
def index() -> FileResponse:
    return FileResponse(
        WEB / "studio.html",
        media_type="text/html; charset=utf-8",
        headers={"Cache-Control": "no-store"},
    )


@app.get("/studio")
def studio() -> FileResponse:
    return FileResponse(
        WEB / "studio.html",
        media_type="text/html; charset=utf-8",
        headers={"Cache-Control": "no-store"},
    )


@app.get("/health")
def health() -> dict:
    status = config.safe_status()
    return {
        "ok": True,
        "project": "AstraCore OS",
        "cost_mode": "paid_enabled" if status["paid_models_enabled"] else "local_first",
        "outputs_dir": str(OUTPUTS),
        "active_provider": status["active_provider"],
    }


@app.get("/api/config/status")
def config_status() -> dict:
    return {
        "ok": True,
        "status": config.safe_status(),
    }


@app.get("/api/command-center")
def command_center() -> dict:
    return {
        "ok": True,
        "state": default_command_center_state(ROOT).to_dict(),
    }


@app.get("/api/skills")
def skills() -> dict:
    return {
        "ok": True,
        **skill_catalog(),
    }


@app.get("/api/intel/status")
def intel_status() -> dict:
    return {
        "ok": True,
        **skill_catalog(),
        "notifications": [channel.to_dict() for channel in notification_channels()],
    }


@app.get("/api/integrations/tradingview/status")
def tradingview_status() -> dict:
    return {
        "ok": True,
        "status": tradingview_bridge.status(),
        "example_alert_body": TradingViewBridge.example_alert_body(),
    }


@app.post("/api/integrations/tradingview/webhook")
def tradingview_webhook(payload: dict) -> dict:
    try:
        alert = tradingview_bridge.ingest(payload)
    except PermissionError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    return {
        "ok": True,
        "alert": alert.to_dict(),
    }


@app.post("/api/intel/run")
def run_intel_skill(req: IntelRunRequest) -> dict:
    return intel_runner.run(req.skill_id, req.directive).to_dict()


@app.post("/api/operator")
def run_operator(req: OperatorRequest) -> dict:
    result = agent.run(req.directive)
    return result.__dict__


@app.get("/api/download/{filename}")
def download_output(filename: str) -> FileResponse:
    path = (OUTPUTS / filename).resolve()
    outputs_root = OUTPUTS.resolve()
    if outputs_root not in path.parents or not path.exists() or not path.is_file():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(path, filename=path.name)


@app.get("/api/memory")
def recent_memory(limit: int = 10) -> dict:
    safe_limit = min(max(limit, 1), 50)
    return {
        "ok": True,
        "items": agent.recent_memory(safe_limit),
    }


@app.post("/api/captures")
async def save_capture(request: Request, filename: str = "") -> dict:
    raw = await request.body()
    try:
        session = capture_studio.save_capture(raw, filename)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "ok": True,
        "capture": {
            **session.to_dict(),
            "download_url": f"/captures/{session.filename}",
        },
    }


@app.get("/api/captures")
def list_captures(limit: int = 20) -> dict:
    safe_limit = min(max(limit, 1), 50)
    return {
        "ok": True,
        "captures": [
            {
                **session.to_dict(),
                "download_url": f"/captures/{session.filename}",
            }
            for session in capture_studio.recent_captures(safe_limit)
        ],
    }


@app.post("/api/strategies/pine")
def generate_pine_strategy(req: PineStrategyRequest) -> dict:
    artifact = pine_generator.generate_scalp_assist(req.notes, req.name)
    return {
        "ok": True,
        "strategy": {
            **artifact.to_dict(),
            "download_url": f"/outputs/{artifact.filename}",
        },
    }
