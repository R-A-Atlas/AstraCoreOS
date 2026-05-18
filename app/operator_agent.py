from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
import json
import re
from typing import Any
from uuid import uuid4

from app.agent_packets import ContextPacket
from app.agents.business_documentation_agent import BusinessDocumentationAgent
from app.model_router import ModelRouter
from app.synthesizer import AnswerSynthesizer
from app.tools.document_writer import build_business_document_markdown, write_docx


@dataclass
class OperatorResult:
    ok: bool
    message: str
    mode: str
    model: dict[str, Any]
    steps: list[dict[str, str]]
    artifacts: list[dict[str, str]]
    memory: list[str]
    context_packets: list[dict[str, Any]]


class OperatorAgent:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.outputs_dir = root / "workspace" / "outputs"
        self.memory_path = root / "workspace" / "memory" / "events.jsonl"
        self.router = ModelRouter()
        self.business_docs = BusinessDocumentationAgent()
        self.synthesizer = AnswerSynthesizer()

    def run(self, directive: str) -> OperatorResult:
        text = (directive or "").strip()
        if not text:
            return self._simple("I need a directive first.", "chat")

        if self._wants_business_documentation(text):
            return self._run_business_documentation(text)

        if self._is_greeting(text):
            return self._simple("I'm good. What do you want to test first?", "chat")

        if self._asks_capabilities(text):
            return self._simple(
                "Right now I can chat locally and use the Business Documentation Agent to create practical plans, reports, SOPs, and proposals as real Word documents.",
                "chat",
            )

        return self._simple(
            "I can start with local tools first. Try: create a one-page business plan, SOP, proposal, or finance report and save it as a Word document.",
            "chat",
        )

    def recent_memory(self, limit: int = 10) -> list[dict[str, Any]]:
        if not self.memory_path.exists():
            return []
        rows: list[dict[str, Any]] = []
        with self.memory_path.open("r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError:
                    rows.append({"error": "corrupt_memory_row", "raw": line})
        return rows[-limit:]

    def _run_business_documentation(self, directive: str) -> OperatorResult:
        packet = self.business_docs.gather(directive)
        decision = self.router.decide("document", "low")
        title = self._document_title(packet)
        markdown = build_business_document_markdown(title, packet.data)
        artifacts = []
        if packet.data.get("format") == "docx":
            artifact = write_docx(
                title,
                markdown,
                self.outputs_dir,
                summary=f"Created from {packet.agent}: {packet.summary}",
            )
            artifacts.append(
                {
                    "id": str(uuid4()),
                    "title": artifact.title,
                    "kind": artifact.kind,
                    "summary": artifact.summary,
                    "path": str(artifact.path),
                    "download_url": f"/outputs/{artifact.path.name}",
                }
            )
        artifact_titles = [item["title"] for item in artifacts]
        message = self.synthesizer.synthesize(directive, [packet], artifact_titles)
        memory = [
            packet.summary,
            f"First active agent: {packet.agent}.",
        ]
        self._write_memory(directive, memory, artifacts[0]["path"] if artifacts else None, [packet])
        steps = [
            {"label": "Interpreted directive", "detail": "Detected a business documentation request."},
            {"label": "Activated agent", "detail": packet.agent},
            {"label": "Selected route", "detail": decision.reason},
            {"label": "Built packet", "detail": packet.summary},
        ]
        if artifacts:
            steps.extend(
                [
                    {"label": "Used tool", "detail": "document_writer.write_docx"},
                    {"label": "Created artifact", "detail": artifacts[0]["path"]},
                ]
            )
        return OperatorResult(
            ok=True,
            message=message,
            mode="document" if artifacts else "agent_packet",
            model=asdict(decision),
            steps=steps,
            artifacts=artifacts,
            memory=memory,
            context_packets=[packet.to_dict()],
        )

    def _simple(self, message: str, mode: str) -> OperatorResult:
        decision = self.router.decide("chat", "low")
        return OperatorResult(
            ok=True,
            message=message,
            mode=mode,
            model=asdict(decision),
            steps=[{"label": "Local response", "detail": "No paid model call used."}],
            artifacts=[],
            memory=[],
            context_packets=[],
        )

    def _write_memory(
        self,
        directive: str,
        memory: list[str],
        artifact_path: str | Path | None,
        packets: list[ContextPacket] | None = None,
    ) -> None:
        self.memory_path.parent.mkdir(parents=True, exist_ok=True)
        record = {
            "directive": directive,
            "memory": memory,
            "artifact_path": str(artifact_path) if artifact_path else None,
            "context_packets": [packet.to_dict() for packet in packets or []],
        }
        with self.memory_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record) + "\n")

    @staticmethod
    def _is_greeting(text: str) -> bool:
        return bool(re.match(r"^\s*(hi|hey|hello|yo|how are you|what's up)\b", text, re.I))

    @staticmethod
    def _asks_capabilities(text: str) -> bool:
        return bool(re.search(r"\bwhat can you do\b|\bhow does this work\b|\bwhat works\b", text, re.I))

    @staticmethod
    def _wants_business_documentation(text: str) -> bool:
        q = text.lower()
        doc_words = [
            "business plan",
            "word document",
            "docx",
            "document",
            "file",
            "proposal",
            "sop",
            "checklist",
            "finance report",
            "financial report",
            "one-page report",
            "one page report",
        ]
        business_words = ["business", "company", "service", "startup", "client", "bakery", "detailing", "cleaning"]
        return any(word in q for word in doc_words) and any(word in q for word in business_words)

    @staticmethod
    def _document_title(packet: ContextPacket) -> str:
        business = str(packet.data.get("business", "Business")).title()
        doc_type = str(packet.data.get("document_type", "Document")).replace("_", " ").title()
        return f"{business} {doc_type}"
