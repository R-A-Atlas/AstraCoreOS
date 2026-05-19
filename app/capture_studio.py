from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import json
import re
from pathlib import Path
from uuid import uuid4


@dataclass
class CaptureSession:
    id: str
    filename: str
    path: str
    size_bytes: int
    created_at: str
    transcript_status: str
    analysis_status: str
    transcript_filename: str = ""
    transcript_path: str = ""
    display_name: str = ""
    tags: list[str] = field(default_factory=list)
    notes_summary: str = ""
    last_exported_at: str = ""
    generated_exports: list[dict] = field(default_factory=list)
    ai_review_status: str = "not_started"
    mistake_markers: list[dict] = field(default_factory=list)
    setup_type: str = ""
    trade_grade: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


class CaptureStudio:
    def __init__(self, root: Path) -> None:
        self.capture_dir = root / "workspace" / "captures"
        self.index_path = self.capture_dir / "capture_sessions.jsonl"

    def save_capture(self, raw: bytes, filename: str | None = None, transcript: str = "") -> CaptureSession:
        if not raw:
            raise ValueError("Capture file is empty.")
        self.capture_dir.mkdir(parents=True, exist_ok=True)
        safe_name = self._safe_filename(filename)
        path = self.capture_dir / safe_name
        path.write_bytes(raw)
        transcript_filename = ""
        transcript_path = ""
        transcript = transcript.strip()
        if transcript:
            transcript_filename = f"{Path(safe_name).stem}.txt"
            transcript_file = self.capture_dir / transcript_filename
            transcript_file.write_text(transcript + "\n", encoding="utf-8")
            transcript_path = str(transcript_file)
        session = CaptureSession(
            id=str(uuid4()),
            filename=safe_name,
            path=str(path),
            size_bytes=len(raw),
            created_at=datetime.now(timezone.utc).isoformat(),
            transcript_status="complete" if transcript else "pending",
            analysis_status="pending",
            transcript_filename=transcript_filename,
            transcript_path=transcript_path,
            display_name=Path(safe_name).stem,
        )
        self._append_session(session)
        return session

    def all_captures(self) -> list[CaptureSession]:
        if not self.index_path.exists():
            return []
        sessions: list[CaptureSession] = []
        with self.index_path.open("r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    sessions.append(self._session_from_payload(json.loads(line)))
                except (json.JSONDecodeError, TypeError):
                    continue
        return sessions

    def recent_captures(self, limit: int = 20, offset: int = 0) -> list[CaptureSession]:
        sessions = self.all_captures()
        if offset:
            sessions = sessions[:-offset] if offset < len(sessions) else []
        return sessions[-limit:]

    def paged_captures(self, limit: int = 20, offset: int = 0) -> list[CaptureSession]:
        return list(reversed(self.all_captures()))[offset : offset + limit]

    def get_capture(self, capture_id: str) -> CaptureSession | None:
        for session in self.all_captures():
            if session.id == capture_id:
                return session
        return None

    def update_capture(
        self,
        capture_id: str,
        display_name: str | None = None,
        tags: list[str] | None = None,
        notes_summary: str | None = None,
    ) -> CaptureSession:
        sessions = self.all_captures()
        target: CaptureSession | None = None
        for session in sessions:
            if session.id != capture_id:
                continue
            if display_name is not None:
                session.display_name = self._safe_display_name(display_name) or session.display_name
            if tags is not None:
                session.tags = [tag for raw in tags if (tag := self._safe_tag(raw))][:12]
            if notes_summary is not None:
                session.notes_summary = notes_summary.strip()[:500]
            target = session
            break
        if target is None:
            raise KeyError("Capture not found.")
        self._write_sessions(sessions)
        return target

    def delete_capture(self, capture_id: str) -> CaptureSession:
        sessions = self.all_captures()
        kept: list[CaptureSession] = []
        target: CaptureSession | None = None
        for session in sessions:
            if session.id == capture_id:
                target = session
            else:
                kept.append(session)
        if target is None:
            raise KeyError("Capture not found.")
        self._delete_file(target.path)
        self._delete_file(target.transcript_path)
        self._write_sessions(kept)
        return target

    def transcript_for(self, capture_id: str) -> str:
        session = self.get_capture(capture_id)
        if session is None:
            raise KeyError("Capture not found.")
        if not session.transcript_path:
            return ""
        path = Path(session.transcript_path)
        if path.exists() and path.is_file():
            return path.read_text(encoding="utf-8").strip()
        return ""

    def record_export(self, capture_id: str, export_type: str, artifact: object) -> CaptureSession:
        sessions = self.all_captures()
        target: CaptureSession | None = None
        created_at = datetime.now(timezone.utc).isoformat()
        for session in sessions:
            if session.id != capture_id:
                continue
            session.generated_exports.append(
                {
                    "type": export_type,
                    "filename": getattr(artifact, "filename", ""),
                    "title": getattr(artifact, "title", ""),
                    "created_at": created_at,
                }
            )
            session.generated_exports = session.generated_exports[-20:]
            session.last_exported_at = created_at
            target = session
            break
        if target is None:
            raise KeyError("Capture not found.")
        self._write_sessions(sessions)
        return target

    def latest_transcript(self) -> str:
        for session in reversed(self.recent_captures(50)):
            if not session.transcript_path:
                continue
            path = Path(session.transcript_path)
            if path.exists() and path.is_file():
                text = path.read_text(encoding="utf-8").strip()
                if text:
                    return text
        return ""

    def _append_session(self, session: CaptureSession) -> None:
        self.capture_dir.mkdir(parents=True, exist_ok=True)
        with self.index_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(session.to_dict()) + "\n")

    def _write_sessions(self, sessions: list[CaptureSession]) -> None:
        self.capture_dir.mkdir(parents=True, exist_ok=True)
        with self.index_path.open("w", encoding="utf-8") as fh:
            for session in sessions:
                fh.write(json.dumps(session.to_dict()) + "\n")

    def _session_from_payload(self, payload: dict) -> CaptureSession:
        payload = dict(payload)
        payload.setdefault("transcript_filename", "")
        payload.setdefault("transcript_path", "")
        payload.setdefault("display_name", Path(payload.get("filename", "capture")).stem)
        payload.setdefault("tags", [])
        payload.setdefault("notes_summary", "")
        payload.setdefault("last_exported_at", "")
        payload.setdefault("generated_exports", [])
        payload.setdefault("ai_review_status", "not_started")
        payload.setdefault("mistake_markers", [])
        payload.setdefault("setup_type", "")
        payload.setdefault("trade_grade", "")
        return CaptureSession(**payload)

    def _delete_file(self, raw_path: str) -> None:
        if not raw_path:
            return
        path = Path(raw_path).resolve()
        capture_root = self.capture_dir.resolve()
        if capture_root not in path.parents:
            return
        if path.exists() and path.is_file():
            path.unlink()

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

    @staticmethod
    def _safe_display_name(value: str) -> str:
        return re.sub(r"\s+", " ", (value or "").strip())[:120]

    @staticmethod
    def _safe_tag(value: str) -> str:
        return re.sub(r"[^a-zA-Z0-9 _-]+", "", (value or "").strip())[:32]
