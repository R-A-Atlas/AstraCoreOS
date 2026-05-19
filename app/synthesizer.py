from __future__ import annotations

import json

from app.agent_packets import ContextPacket
from app.model_clients import GeminiClient, ModelClientError
from app.model_router import ModelDecision


class AnswerSynthesizer:
    def synthesize(
        self,
        directive: str,
        packets: list[ContextPacket],
        artifact_titles: list[str] | None = None,
        decision: ModelDecision | None = None,
    ) -> str:
        if decision and decision.paid_call_allowed and decision.provider == "gemini":
            try:
                return self._synthesize_with_gemini(directive, packets, artifact_titles or [], decision)
            except ModelClientError as exc:
                return f"Local fallback used because Gemini was unavailable: {exc}"

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

    def _synthesize_with_gemini(
        self,
        directive: str,
        packets: list[ContextPacket],
        artifact_titles: list[str],
        decision: ModelDecision,
    ) -> str:
        client = GeminiClient(model=decision.model)
        packet_payload = [packet.to_dict() for packet in packets]
        prompt = (
            "You are AstraCore, a practical agentic operating system assistant.\n"
            "The user talks to you naturally. Specialist agents gather context packets; they do not answer the user.\n"
            "Use the packet data first. If details are missing, say exactly what is missing without inventing facts.\n"
            "Keep the answer natural, direct, and useful. Do not mention internal implementation unless helpful.\n\n"
            f"User directive:\n{directive}\n\n"
            f"Created artifacts:\n{json.dumps(artifact_titles, indent=2)}\n\n"
            f"Context packets:\n{json.dumps(packet_payload, indent=2)}\n\n"
            "Write the final user-facing response."
        )
        return client.generate(prompt)
