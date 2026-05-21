from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import time
from typing import Any

from app.config import env_bool, env_int, load_env_file
from app.model_clients import GeminiClient, ModelClientError
from app.pine_generator import PineStrategyGenerator, StrategyArtifact


class AIBrainError(RuntimeError):
    pass


@dataclass(frozen=True)
class AIBrainResult:
    artifact: StrategyArtifact
    export_type: str
    source: str
    model: str


class GeminiMultimodalClient:
    def __init__(self, api_key: str | None = None, model: str | None = None) -> None:
        self.api_key = (api_key or os.getenv("GEMINI_API_KEY", "")).strip()
        self.model = (model or os.getenv("GEMINI_MODEL_MULTIMODAL", "gemini-2.5-flash")).strip()

    @property
    def configured(self) -> bool:
        return bool(self.api_key)

    def generate_from_video(self, video_path: Path, prompt: str) -> str:
        if not self.configured:
            raise ModelClientError("Gemini API key missing.")
        if not video_path.exists() or not video_path.is_file():
            raise ModelClientError("Selected capture video file is missing.")
        try:
            from google import genai
            from google.genai import types
        except ImportError as exc:
            raise ModelClientError("google-genai is not installed. Run pip install -r requirements.txt.") from exc

        client = genai.Client(api_key=self.api_key)
        try:
            uploaded = client.files.upload(file=str(video_path))
            uploaded_name = getattr(uploaded, "name", "")
            wait_seconds = max(30, env_int("GEMINI_FILE_ACTIVE_TIMEOUT_SECONDS", 900))
            poll_seconds = max(1, env_int("GEMINI_FILE_POLL_SECONDS", 5))
            deadline = time.time() + wait_seconds
            active = False
            while uploaded_name and time.time() < deadline:
                current = client.files.get(name=uploaded_name)
                state = str(getattr(getattr(current, "state", ""), "name", getattr(current, "state", ""))).upper()
                if state == "ACTIVE":
                    uploaded = current
                    active = True
                    break
                if state == "FAILED":
                    raise ModelClientError("Gemini video processing failed.")
                time.sleep(poll_seconds)
            if uploaded_name and not active:
                raise ModelClientError(f"Gemini video processing timed out after {wait_seconds} seconds before the file became active.")
            response = client.models.generate_content(
                model=self.model,
                contents=[uploaded, prompt],
                config=types.GenerateContentConfig(response_mime_type="application/json"),
            )
        except Exception as exc:
            raise ModelClientError(f"Gemini multimodal request failed: {exc}") from exc
        text = getattr(response, "text", None)
        if not text:
            raise ModelClientError("Gemini returned an empty multimodal response.")
        return str(text).strip()


class MultimodalAIBrain:
    def __init__(
        self,
        root: Path,
        generator: PineStrategyGenerator,
        client: GeminiMultimodalClient | None = None,
        text_client: GeminiClient | None = None,
    ) -> None:
        load_env_file(root / ".env")
        self.root = root
        self.generator = generator
        self.client = client or GeminiMultimodalClient()
        self.text_client = text_client or GeminiClient(model=os.getenv("GEMINI_MODEL_DEFAULT", "gemini-2.5-flash"))

    @property
    def enabled(self) -> bool:
        return env_bool("ASTRA_AI_BRAIN_ENABLED", False) and env_bool("ASTRA_AI_EXPORTS_ENABLED", False)

    @property
    def reviews_enabled(self) -> bool:
        return env_bool("ASTRA_AI_BRAIN_ENABLED", False) and env_bool("ASTRA_AI_REVIEWS_ENABLED", False)

    @property
    def fallback_to_local(self) -> bool:
        return env_bool("ASTRA_AI_FALLBACK_TO_LOCAL", False)

    def generate_export(
        self,
        session: Any,
        transcript: str,
        name: str,
        export_type: str,
        review: dict[str, Any] | None = None,
        memory_summary: dict[str, Any] | None = None,
    ) -> AIBrainResult:
        clean_export_type = self._normalize_export_type(export_type)
        self._validate_review_export_ready(review)
        prompt = self._build_review_export_prompt(transcript, name, clean_export_type, review, memory_summary)
        try:
            raw = self.text_client.generate(prompt)
        except ModelClientError as exc:
            raise AIBrainError(str(exc)) from exc
        parsed = self._parse_response(raw, clean_export_type)
        content = parsed["content"].strip()
        if not content:
            raise AIBrainError("AI Brain returned empty export content.")
        title = parsed.get("title") or name
        summary = parsed.get("summary") or "Generated by AstraCore multimodal AI Brain from video plus voice/transcript context."
        artifact = self.generator.write_custom_artifact(content, title, clean_export_type, summary)
        return AIBrainResult(
            artifact=artifact,
            export_type=clean_export_type,
            source="ai_review_memory",
            model=self.text_client.model,
        )

    def generate_review(
        self,
        session: Any,
        transcript: str,
        memory_summary: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        self._validate_ready(session, transcript, "review")
        prompt = self._build_review_prompt(transcript, memory_summary)
        try:
            raw = self.client.generate_from_video(Path(session.path), prompt)
        except ModelClientError as exc:
            raise AIBrainError(str(exc)) from exc
        review = self._parse_review_response(raw)
        review["capture_id"] = str(getattr(session, "id", ""))
        review["source"] = "ai_multimodal_review"
        review["model"] = self.client.model
        review["created_at"] = datetime.now(timezone.utc).isoformat()
        return review

    def _validate_ready(self, session: Any, transcript: str, mode: str) -> None:
        if mode == "review":
            if not self.reviews_enabled:
                raise AIBrainError("AI reviews disabled.")
        elif not self.enabled:
            raise AIBrainError("AI Brain disabled.")
        if os.getenv("ASTRA_AI_BRAIN_PROVIDER", "gemini").strip().lower() != "gemini":
            raise AIBrainError("Only Gemini multimodal AI Brain is wired in this build.")
        if not self.client.configured:
            raise AIBrainError("Gemini API key missing.")
        video_path = Path(getattr(session, "path", ""))
        if env_bool("ASTRA_AI_REQUIRE_VIDEO", True) and (not video_path.exists() or not video_path.is_file()):
            raise AIBrainError("Selected capture video file is missing.")
        has_audio_or_transcript = bool(getattr(session, "mic_enabled", False)) or bool(transcript.strip())
        if env_bool("ASTRA_AI_REQUIRE_AUDIO_OR_TRANSCRIPT", True) and not has_audio_or_transcript:
            raise AIBrainError(f"Selected capture needs mic audio or a transcript before AI {mode}.")

    def _validate_review_export_ready(self, review: dict[str, Any] | None) -> None:
        if not self.enabled:
            raise AIBrainError("AI Brain disabled.")
        if os.getenv("ASTRA_AI_BRAIN_PROVIDER", "gemini").strip().lower() != "gemini":
            raise AIBrainError("Only Gemini AI Brain is wired in this build.")
        if not review:
            raise AIBrainError("Run AI Review before AI export.")
        if not self.text_client.configured:
            raise AIBrainError("Gemini API key missing.")

    @staticmethod
    def _normalize_export_type(export_type: str) -> str:
        clean = export_type.strip().lower()
        if clean == "pine":
            return "pine"
        if clean in {"mt5", "mql5"}:
            return "mt5"
        if clean in {"instructions", "brief", "markdown"}:
            return "instructions"
        raise AIBrainError("Unsupported export type.")

    @staticmethod
    def _parse_response(raw: str, export_type: str) -> dict[str, str]:
        text = MultimodalAIBrain._strip_json_fence(raw)
        try:
            payload = json.loads(text)
        except json.JSONDecodeError as exc:
            raise AIBrainError("AI Brain response was not valid JSON.") from exc
        if not isinstance(payload, dict):
            raise AIBrainError("AI Brain response must be a JSON object.")
        exports = payload.get("exports", {})
        content = ""
        if isinstance(exports, dict):
            content = str(exports.get(export_type) or "")
        if not content:
            content = str(payload.get("content") or "")
        return {
            "title": str(payload.get("title") or "AstraCore AI Strategy"),
            "summary": str(payload.get("summary") or ""),
            "content": content,
        }

    @staticmethod
    def _parse_review_response(raw: str) -> dict[str, Any]:
        text = MultimodalAIBrain._strip_json_fence(raw)
        try:
            payload = json.loads(text)
        except json.JSONDecodeError as exc:
            raise AIBrainError("AI review response was not valid JSON.") from exc
        if not isinstance(payload, dict):
            raise AIBrainError("AI review response must be a JSON object.")
        return {
            "summary": str(payload.get("summary") or ""),
            "trade_grade": str(payload.get("trade_grade") or "Ungraded"),
            "setup_type": str(payload.get("setup_type") or "Unclassified"),
            "strengths": payload.get("strengths") if isinstance(payload.get("strengths"), list) else [],
            "mistakes": payload.get("mistakes") if isinstance(payload.get("mistakes"), list) else [],
            "timestamped_notes": payload.get("timestamped_notes") if isinstance(payload.get("timestamped_notes"), list) else [],
            "strategy_rules": payload.get("strategy_rules") if isinstance(payload.get("strategy_rules"), list) else [],
            "next_practice_focus": str(payload.get("next_practice_focus") or ""),
            "voice_summary": str(payload.get("voice_summary") or payload.get("summary") or ""),
        }

    @staticmethod
    def _strip_json_fence(raw: str) -> str:
        text = raw.strip()
        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?", "", text, flags=re.IGNORECASE).strip()
            text = re.sub(r"```$", "", text).strip()
        return text

    @staticmethod
    def _build_prompt(
        transcript: str,
        name: str,
        export_type: str,
        review: dict[str, Any] | None = None,
        memory_summary: dict[str, Any] | None = None,
    ) -> str:
        output_instruction = {
            "pine": "Return a complete TradingView Pine Script v6 strategy. Include entries, invalidation, targets, alerts, and minimal chart clutter.",
            "mt5": "Return a complete MT5/MQL5 Expert Advisor starter. Include entries, invalidation, targets, risk inputs, and comments.",
            "instructions": "Return a complete visual HTML strategy playbook. It should be readable, practical, and specific to what is shown and explained.",
        }[export_type]
        transcript_block = transcript.strip() or "Transcript sidecar missing. Use the video audio and chart visuals as primary context."
        review_block = json.dumps(review or {}, indent=2)[:6000]
        memory_block = json.dumps(memory_summary or {}, indent=2)[:6000]
        return f"""
You are AstraCore's multimodal trading strategy extraction brain.

Analyze the attached chart walkthrough video and its embedded audio. Use the transcript only as supporting text.
Do not create rules from transcript alone. Use visual chart context: instrument/timeframe labels when visible, indicators, range size, range high/low, midpoint, liquidity zones, entry examples, invalidation, targets, and what the trader points to or describes.
Use the saved AI review and trading memory as additional context when present. If memory conflicts with the selected video, prioritize the selected video.

Requested export name: {name}
Requested export type: {export_type}

Transcript sidecar:
{transcript_block}

Saved AI review for this capture:
{review_block}

Trading memory summary:
{memory_block}

{output_instruction}

Return only JSON with this shape:
{{
  "title": "short strategy name",
  "summary": "one sentence summary",
  "exports": {{
    "{export_type}": "full file content as a string"
  }}
}}
"""

    @staticmethod
    def _build_review_export_prompt(
        transcript: str,
        name: str,
        export_type: str,
        review: dict[str, Any] | None,
        memory_summary: dict[str, Any] | None = None,
    ) -> str:
        output_instruction = {
            "pine": "Return a complete TradingView Pine Script v6 strategy. Include entries, invalidation, targets, alerts, and minimal chart clutter.",
            "mt5": "Return a complete MT5/MQL5 Expert Advisor starter. Include entries, invalidation, targets, risk inputs, and comments.",
            "instructions": "Return a complete visual HTML strategy playbook. It should be readable, practical, and specific to the saved review.",
        }[export_type]
        transcript_block = transcript.strip()[:12000] or "Transcript sidecar missing."
        review_block = json.dumps(review or {}, indent=2)[:10000]
        memory_block = json.dumps(memory_summary or {}, indent=2)[:6000]
        return f"""
You are AstraCore's strategy export brain.

Generate the requested trading strategy artifact from the saved multimodal AI review, transcript, and trading memory.
Do not claim you watched the video in this step. The video was already reviewed in the saved AI review.
Prioritize the saved AI review's setup type, timestamped notes, mistakes, strengths, and strategy rules.
Use the transcript only to preserve trader terminology and indicator names.

Requested export name: {name}
Requested export type: {export_type}

Saved AI review:
{review_block}

Trading memory summary:
{memory_block}

Transcript:
{transcript_block}

{output_instruction}

Return only JSON with this shape:
{{
  "title": "short strategy name",
  "summary": "one sentence summary",
  "exports": {{
    "{export_type}": "full file content as a string"
  }}
}}
"""

    @staticmethod
    def _build_review_prompt(transcript: str, memory_summary: dict[str, Any] | None = None) -> str:
        transcript_block = transcript.strip() or "Transcript sidecar missing. Use the video audio and chart visuals as primary context."
        memory_block = json.dumps(memory_summary or {}, indent=2)[:6000]
        return f"""
You are AstraCore's direct trading coach.

Review the attached chart walkthrough video and embedded audio. Use the transcript only as supporting text.
Be direct and practical. Call out early entries, hesitation, unclear invalidation, weak context, chasing, and missed confirmation when visible or narrated.
Do not invent a trade that is not visible or explained. If something is unclear, say it is unclear.
Use timestamped notes whenever possible.

Transcript sidecar:
{transcript_block}

Existing trading memory summary:
{memory_block}

Return only JSON with this exact shape:
{{
  "summary": "short direct review",
  "trade_grade": "A/B/C/D/F or Ungraded",
  "setup_type": "specific setup classification",
  "strengths": ["specific thing done well"],
  "mistakes": ["specific mistake or risk"],
  "timestamped_notes": [
    {{
      "timecode": "MM:SS",
      "label": "short label",
      "observation": "what happened",
      "coaching_note": "what to do next time",
      "severity": "low|medium|high|critical"
    }}
  ],
  "strategy_rules": ["rule this session suggests keeping"],
  "next_practice_focus": "one focused action for the next session",
  "voice_summary": "one short paragraph that can be spoken by a future Jarvis voice"
}}
"""
