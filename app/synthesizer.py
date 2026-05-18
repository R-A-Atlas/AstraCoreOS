from __future__ import annotations

from app.agent_packets import ContextPacket


class AnswerSynthesizer:
    def synthesize(
        self,
        directive: str,
        packets: list[ContextPacket],
        artifact_titles: list[str] | None = None,
    ) -> str:
        if not packets:
            return "I can handle that. Tell me what output you want and I will route the next step."

        packet = packets[0]
        doc_type = str(packet.data.get("document_type", "document")).replace("_", " ")
        business = str(packet.data.get("business", "the business"))
        fmt = str(packet.data.get("format", "chat"))
        title = artifact_titles[0] if artifact_titles else None

        if fmt == "docx" and title:
            return f"Done. I created a real Word document: {title}. I used the {packet.agent} packet as the source context."
        if fmt == "pdf" and title:
            return f"Done. I created a PDF-ready document: {title}. I used the {packet.agent} packet as the source context."
        return (
            f"I prepared a {doc_type} framework for {business}. "
            f"The agent packet is on the visor with the sections, assumptions, sources, and warnings."
        )
