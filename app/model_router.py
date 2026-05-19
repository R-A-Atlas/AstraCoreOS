from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path

from app.config import env_bool, env_int, load_env_file


@dataclass(frozen=True)
class ModelDecision:
    provider: str
    model: str
    reason: str
    estimated_cost_usd: float
    paid_call_allowed: bool


class ModelRouter:
    """Cheap-first model routing.

    This does not call paid APIs yet. It gives the OS a stable decision layer so
    we can later plug in OpenAI, Gemini, Claude, DeepSeek, or local models
    without rewriting the agent.
    """

    def __init__(self, root: Path | None = None) -> None:
        if root is not None:
            load_env_file(root / ".env")
        self.provider = os.getenv("ASTRA_MODEL_PROVIDER", "local").strip().lower() or "local"
        self.paid_enabled = env_bool("ENABLE_PAID_MODELS", False)
        self.max_paid_calls = env_int("ASTRA_MAX_PAID_CALLS_PER_DAY", 0)

    def decide(self, task_type: str, complexity: str = "low") -> ModelDecision:
        if self.provider == "local" or not self.paid_enabled or self.max_paid_calls <= 0:
            return ModelDecision(
                provider="local",
                model="local-tools-v0",
                reason="Local tool path selected to avoid paid model spend.",
                estimated_cost_usd=0.0,
                paid_call_allowed=False,
            )

        if complexity == "high":
            return ModelDecision(
                os.getenv("ASTRA_TIER3_PROVIDER", "openai"),
                os.getenv("OPENAI_MODEL_REASONING", "gpt-5.5"),
                "High complexity reasoning lane.",
                0.02,
                True,
            )
        if task_type in {"research", "web"}:
            return ModelDecision(
                os.getenv("ASTRA_TIER2_PROVIDER", "gemini"),
                os.getenv("GEMINI_MODEL_DEFAULT", "gemini-2.5-flash"),
                "Cheap web/research lane.",
                0.005,
                True,
            )
        if task_type == "coding":
            return ModelDecision(
                "deepseek",
                os.getenv("DEEPSEEK_MODEL_DEFAULT", "deepseek-v4-flash"),
                "Low-cost coding lane.",
                0.003,
                True,
            )
        return ModelDecision(
            self.provider,
            os.getenv(f"{self.provider.upper()}_MODEL", os.getenv("GEMINI_MODEL_DEFAULT", "gemini-2.5-flash")),
            "Paid model route selected by configuration.",
            0.005,
            True,
        )
