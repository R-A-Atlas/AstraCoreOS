from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from app.ai_brain import AIBrainError, MultimodalAIBrain
from app.command_center import default_command_center_state
from app.config import AppConfig
from app.capture_studio import CaptureStudio
from app.intel_runner import IntelRunner
from app.notifications import notification_channels
from app.operator_agent import OperatorAgent
from app.pine_generator import PineStrategyGenerator
from app.skills_registry import skill_catalog
from app.trading_memory import TradingMemory
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
ai_brain = MultimodalAIBrain(ROOT, pine_generator)
trading_memory = TradingMemory(ROOT)

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
    export_type: str = Field("pine", max_length=20)


class CaptureUpdateRequest(BaseModel):
    display_name: str | None = Field(None, max_length=120)
    tags: list[str] | None = None
    notes_summary: str | None = Field(None, max_length=500)


class CaptureExportRequest(BaseModel):
    name: str = Field("AstraCore Scalp Assist", max_length=100)
    export_type: str = Field("pine", max_length=20)
    export_mode: str = Field("ai", max_length=20)


@app.get("/")
def index() -> FileResponse:
    return FileResponse(
        WEB / "landing.html",
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


@app.get("/library")
def capture_library() -> FileResponse:
    return FileResponse(
        WEB / "library.html",
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
async def save_capture(request: Request, filename: str = "", transcript: str = "", mic_enabled: bool = False) -> dict:
    raw = await request.body()
    try:
        session = capture_studio.save_capture(raw, filename, transcript, mic_enabled)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    transcript_download_url = (
        f"/captures/{session.transcript_filename}" if session.transcript_filename else ""
    )
    return {
        "ok": True,
        "capture": {
            **session.to_dict(),
            "download_url": f"/captures/{session.filename}",
            "transcript_download_url": transcript_download_url,
        },
    }


def _capture_payload(session) -> dict:
    review = trading_memory.get_review(session)
    return {
        **session.to_dict(),
        "download_url": f"/captures/{session.filename}",
        "transcript_download_url": (
            f"/captures/{session.transcript_filename}" if session.transcript_filename else ""
        ),
        "has_ai_review": bool(review),
        "review": review,
    }


def _build_strategy_artifact(notes: str, name: str, export_type: str):
    clean_export_type = export_type.strip().lower()
    if clean_export_type == "pine":
        return pine_generator.generate_scalp_assist(notes, name), "pine"
    if clean_export_type in {"mt5", "mql5"}:
        return pine_generator.generate_mql5_expert(notes, name), "mt5"
    if clean_export_type in {"instructions", "brief", "markdown"}:
        return pine_generator.generate_instruction_brief(notes, name), "instructions"
    raise HTTPException(status_code=400, detail="Unsupported export type.")


@app.get("/api/captures")
def list_captures(limit: int = 20, offset: int = 0) -> dict:
    safe_limit = min(max(limit, 1), 50)
    safe_offset = max(offset, 0)
    captures = capture_studio.paged_captures(safe_limit, safe_offset)
    return {
        "ok": True,
        "captures": [_capture_payload(session) for session in captures],
        "total": len(capture_studio.all_captures()),
        "limit": safe_limit,
        "offset": safe_offset,
    }


@app.patch("/api/captures/{capture_id}")
def update_capture(capture_id: str, req: CaptureUpdateRequest) -> dict:
    try:
        session = capture_studio.update_capture(
            capture_id,
            display_name=req.display_name,
            tags=req.tags,
            notes_summary=req.notes_summary,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"ok": True, "capture": _capture_payload(session)}


@app.delete("/api/captures/{capture_id}")
def delete_capture(capture_id: str) -> dict:
    try:
        session = capture_studio.delete_capture(capture_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"ok": True, "deleted": session.id}


@app.get("/api/trading-memory/summary")
def trading_memory_summary() -> dict:
    return {
        "ok": True,
        "summary": trading_memory.summary(),
    }


@app.get("/api/captures/{capture_id}/review")
def get_capture_review(capture_id: str) -> dict:
    session = capture_studio.get_capture(capture_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Capture not found.")
    review = trading_memory.get_review(session)
    if review is None:
        raise HTTPException(status_code=404, detail="AI review not found.")
    return {
        "ok": True,
        "capture": _capture_payload(session),
        "review": review,
    }


@app.post("/api/captures/{capture_id}/review")
def review_capture(capture_id: str) -> dict:
    session = capture_studio.get_capture(capture_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Capture not found.")
    try:
        transcript = capture_studio.transcript_for(capture_id)
        review = ai_brain.generate_review(session, transcript, trading_memory.summary())
        saved_review = trading_memory.save_review(session, review)
        session = capture_studio.record_review(capture_id, saved_review)
    except (AIBrainError, KeyError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "ok": True,
        "capture": _capture_payload(session),
        "review": saved_review,
        "memory": trading_memory.summary(),
    }


@app.post("/api/captures/{capture_id}/export")
def export_capture(capture_id: str, req: CaptureExportRequest) -> dict:
    session = capture_studio.get_capture(capture_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Capture not found.")
    try:
        notes = capture_studio.transcript_for(capture_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    export_mode = req.export_mode.strip().lower() or "ai"
    source = "local_template"
    model = "local-template"
    if export_mode == "local":
        if not notes:
            raise HTTPException(status_code=400, detail="Selected capture has no transcript for Local Template export.")
        artifact, export_type = _build_strategy_artifact(notes, req.name, req.export_type)
    elif export_mode == "ai":
        try:
            result = ai_brain.generate_export(
                session,
                notes,
                req.name,
                req.export_type,
                trading_memory.get_review(session),
                trading_memory.summary(),
            )
        except AIBrainError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        artifact = result.artifact
        export_type = result.export_type
        source = result.source
        model = result.model
    else:
        raise HTTPException(status_code=400, detail="Unsupported export mode.")

    try:
        session = capture_studio.record_export(capture_id, export_type, artifact, source)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {
        "ok": True,
        "capture": _capture_payload(session),
        "strategy": {
            **artifact.to_dict(),
            "download_url": f"/outputs/{artifact.filename}",
            "source": source,
            "model": model,
            "export_type": export_type,
        },
    }


@app.post("/api/strategies/pine")
def generate_pine_strategy(req: PineStrategyRequest) -> dict:
    notes = req.notes.strip() or capture_studio.latest_transcript()
    if not notes:
        raise HTTPException(
            status_code=400,
            detail="No strategy input found. Record a session with transcript or type notes.",
        )
    artifact = pine_generator.generate_scalp_assist(notes, req.name)
    return {
        "ok": True,
        "strategy": {
            **artifact.to_dict(),
            "download_url": f"/outputs/{artifact.filename}",
        },
    }


@app.post("/api/strategies/export")
def generate_strategy_export(req: PineStrategyRequest) -> dict:
    notes = req.notes.strip() or capture_studio.latest_transcript()
    if not notes:
        raise HTTPException(
            status_code=400,
            detail="No strategy input found. Record a session with transcript or type notes.",
        )
    artifact, export_type = _build_strategy_artifact(notes, req.name, req.export_type)
    return {
        "ok": True,
        "strategy": {
            **artifact.to_dict(),
            "download_url": f"/outputs/{artifact.filename}",
            "source": "typed_notes" if req.notes.strip() else "latest_capture_transcript",
            "export_type": export_type,
        },
    }
