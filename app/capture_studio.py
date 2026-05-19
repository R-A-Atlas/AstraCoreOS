from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
import re
from pathlib import Path
from uuid import uuid4


@dataclass(frozen=True)
class CaptureSession:
    id: str
    filename: str
    path: str
    size_bytes: int
    created_at: str
    transcript_status: str
    analysis_status: str

    def to_dict(self) -> dict:
        return asdict(self)


class CaptureStudio:
    def __init__(self, root: Path) -> None:
        self.capture_dir = root / "workspace" / "captures"
        self.index_path = self.capture_dir / "capture_sessions.jsonl"

    def save_capture(self, raw: bytes, filename: str | None = None) -> CaptureSession:
        if not raw:
            raise ValueError("Capture file is empty.")
        self.capture_dir.mkdir(parents=True, exist_ok=True)
        safe_name = self._safe_filename(filename)
        path = self.capture_dir / safe_name
        path.write_bytes(raw)
        session = CaptureSession(
            id=str(uuid4()),
            filename=safe_name,
            path=str(path),
            size_bytes=len(raw),
            created_at=datetime.now(timezone.utc).isoformat(),
            transcript_status="pending",
            analysis_status="pending",
        )
        with self.index_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(session.to_dict()) + "\n")
        return session

    def recent_captures(self, limit: int = 20) -> list[CaptureSession]:
        if not self.index_path.exists():
            return []
        sessions: list[CaptureSession] = []
        with self.index_path.open("r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    sessions.append(CaptureSession(**json.loads(line)))
                except (json.JSONDecodeError, TypeError):
                    continue
        return sessions[-limit:]

    @staticmethod
    def _safe_filename(filename: str | None) -> str:
        base = (filename or "").strip()
        if not base:
            stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
            return f"trade-capture-{stamp}.webm"
        base = re.sub(r"[^a-zA-Z0-9._-]+", "-", base).strip("-._")
        if not base:
            base = "trade-capture"
        if not base.lower().endswith(".webm"):
            base += ".webm"
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        return f"{Path(base).stem}-{stamp}.webm"
