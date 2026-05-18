from __future__ import annotations

from dataclasses import dataclass
import os


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

    def __init__(self) -> None:
        self.mode = os.getenv("ASTRACORE_MODEL_MODE", "local_first").strip().lower()
        self.max_paid_calls = int(os.getenv("ASTRACORE_MAX_PAID_CALLS_PER_DAY", "0") or "0")

    def decide(self, task_type: str, complexity: str = "low") -> ModelDecision:
        if self.mode == "local_first" or self.max_paid_calls <= 0:
            return ModelDecision(
                provider="local",
                model="local-tools-v0",
                reason="Local tool path selected to avoid paid model spend.",
                estimated_cost_usd=0.0,
                paid_call_allowed=False,
            )

        if complexity == "high":
            return ModelDecision("openai", "gpt-5.2", "High complexity reasoning lane.", 0.02, True)
        if task_type in {"research", "web"}:
            return ModelDecision("gemini", "gemini-2.5-flash", "Cheap web/research lane.", 0.005, True)
        if task_type == "coding":
            return ModelDecision("deepseek", "deepseek-v4-flash", "Low-cost coding lane.", 0.003, True)
        return ModelDecision("local", "local-tools-v0", "Local route remains sufficient.", 0.0, False)
