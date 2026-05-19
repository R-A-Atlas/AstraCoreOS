from __future__ import annotations

import os


class ModelClientError(RuntimeError):
    pass


class GeminiClient:
    def __init__(self, api_key: str | None = None, model: str | None = None) -> None:
        self.api_key = (api_key or os.getenv("GEMINI_API_KEY", "")).strip()
        self.model = (model or os.getenv("GEMINI_MODEL", os.getenv("GEMINI_MODEL_DEFAULT", "gemini-2.5-flash"))).strip()

    @property
    def configured(self) -> bool:
        return bool(self.api_key)

    def generate(self, prompt: str) -> str:
        if not self.configured:
            raise ModelClientError("Gemini API key is not configured.")
        try:
            from google import genai
        except ImportError as exc:
            raise ModelClientError("google-genai is not installed. Run pip install -r requirements.txt.") from exc

        client = genai.Client(api_key=self.api_key)
        response = client.models.generate_content(model=self.model, contents=prompt)
        text = getattr(response, "text", None)
        if not text:
            raise ModelClientError("Gemini returned an empty response.")
        return str(text).strip()
