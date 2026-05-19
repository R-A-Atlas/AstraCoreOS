from __future__ import annotations

import json

from app.agent_packets import ContextPacket
from app.model_clients import GeminiClient, ModelClientError
from app.model_router import ModelDecision


class AnswerSynthesizer:
    def synthesize_general(self, directive: str, decision: ModelDecision) -> str:
        if decision.paid_call_allowed and decision.provider == "gemini":
            try:
                return self._general_with_gemini(directive, decision)
            except ModelClientError as exc:
                return f"I can answer that after the model route is available. Gemini fallback reason: {exc}"
        return (
            "I can answer that once the general assistant route is enabled. "
            "Right now the reliable local path is the Business Documentation Agent."
        )

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

    def _general_with_gemini(self, directive: str, decision: ModelDecision) -> str:
        client = GeminiClient(model=decision.model)
        prompt = (
            "You are AstraCore, a practical agentic operating system assistant.\n"
            "Answer the user naturally and directly.\n"
            "Important limitations for this current prototype:\n"
            "- You do not yet have live web search, Google Maps, broker data, or market data tools wired.\n"
            "- If the user asks for current market data, local businesses near them, maps, or live lookup, explain that this tool is not wired yet and give a useful next step or ask what source/location/details they want.\n"
            "- Do not pretend you looked something up if no tool was available.\n"
            "- For business document requests, tell the user to ask for a business plan, SOP, proposal, or finance report if that is what they need.\n\n"
            f"User message:\n{directive}\n\n"
            "Write the final response."
        )
        return client.generate(prompt)
