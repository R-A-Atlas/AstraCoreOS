from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from app.command_center import default_command_center_state
from app.config import AppConfig
from app.intel_runner import IntelRunner
from app.notifications import notification_channels
from app.operator_agent import OperatorAgent
from app.skills_registry import skill_catalog


ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "web"
OUTPUTS = ROOT / "workspace" / "outputs"

app = FastAPI(title="AstraCore OS", version="0.1.0")
config = AppConfig(ROOT)
agent = OperatorAgent(ROOT)
intel_runner = IntelRunner()

app.mount("/static", StaticFiles(directory=WEB), name="static")
app.mount("/outputs", StaticFiles(directory=OUTPUTS), name="outputs")


class OperatorRequest(BaseModel):
    directive: str = Field(..., min_length=1, max_length=4000)
    deep_research: bool = False


class IntelRunRequest(BaseModel):
    skill_id: str = Field(..., min_length=1, max_length=100)
    directive: str = Field("", max_length=4000)


@app.get("/")
def index() -> FileResponse:
    return FileResponse(WEB / "index.html", media_type="text/html; charset=utf-8")


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
        "state": default_command_center_state().to_dict(),
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
