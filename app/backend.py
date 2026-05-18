from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from app.operator_agent import OperatorAgent


ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "web"
OUTPUTS = ROOT / "workspace" / "outputs"

app = FastAPI(title="AstraCore OS", version="0.1.0")
agent = OperatorAgent(ROOT)

app.mount("/static", StaticFiles(directory=WEB), name="static")
app.mount("/outputs", StaticFiles(directory=OUTPUTS), name="outputs")


class OperatorRequest(BaseModel):
    directive: str = Field(..., min_length=1, max_length=4000)


@app.get("/")
def index() -> FileResponse:
    return FileResponse(WEB / "index.html", media_type="text/html; charset=utf-8")


@app.get("/health")
def health() -> dict:
    return {
        "ok": True,
        "project": "AstraCore OS",
        "cost_mode": "local_first",
        "outputs_dir": str(OUTPUTS),
    }


@app.post("/api/operator")
def run_operator(req: OperatorRequest) -> dict:
    result = agent.run(req.directive)
    return result.__dict__


@app.get("/api/memory")
def recent_memory(limit: int = 10) -> dict:
    safe_limit = min(max(limit, 1), 50)
    return {
        "ok": True,
        "items": agent.recent_memory(safe_limit),
    }
