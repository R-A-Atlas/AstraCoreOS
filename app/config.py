from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
from typing import Any


def load_env_file(path: Path, override: bool = True) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and (override or key not in os.environ):
            os.environ[key] = value


def env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def env_int(name: str, default: int = 0) -> int:
    value = os.getenv(name)
    if value is None or not value.strip():
        return default
    try:
        return int(value)
    except ValueError:
        return default


def has_secret(name: str) -> bool:
    return bool(os.getenv(name, "").strip())


@dataclass(frozen=True)
class ProviderStatus:
    provider: str
    configured: bool
    default_model: str
    fast_model: str
    reasoning_model: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "configured": self.configured,
            "default_model": self.default_model,
            "fast_model": self.fast_model,
            "reasoning_model": self.reasoning_model,
        }


class AppConfig:
    def __init__(self, root: Path) -> None:
        self.root = root
        load_env_file(root / ".env")

    @property
    def paid_models_enabled(self) -> bool:
        return env_bool("ENABLE_PAID_MODELS", False)

    @property
    def model_provider(self) -> str:
        return os.getenv("ASTRA_MODEL_PROVIDER", "local").strip().lower() or "local"

    @property
    def max_paid_calls_per_day(self) -> int:
        return env_int("ASTRA_MAX_PAID_CALLS_PER_DAY", 0)

    def safe_status(self) -> dict[str, Any]:
        providers = [
            ProviderStatus(
                provider="gemini",
                configured=has_secret("GEMINI_API_KEY"),
                default_model=os.getenv("GEMINI_MODEL_DEFAULT", "gemini-2.5-flash"),
                fast_model=os.getenv("GEMINI_MODEL_FAST", "gemini-2.5-flash-lite"),
                reasoning_model=os.getenv("GEMINI_MODEL_REASONING", "gemini-2.5-pro"),
            ),
            ProviderStatus(
                provider="openai",
                configured=has_secret("OPENAI_API_KEY"),
                default_model=os.getenv("OPENAI_MODEL_DEFAULT", "gpt-5.4"),
                fast_model=os.getenv("OPENAI_MODEL_FAST", "gpt-5.4-mini"),
                reasoning_model=os.getenv("OPENAI_MODEL_REASONING", "gpt-5.5"),
            ),
            ProviderStatus(
                provider="anthropic",
                configured=has_secret("ANTHROPIC_API_KEY"),
                default_model=os.getenv("ANTHROPIC_MODEL_DEFAULT", "claude-sonnet-4-6"),
                fast_model=os.getenv("ANTHROPIC_MODEL_FAST", "claude-haiku-4-5"),
                reasoning_model=os.getenv("ANTHROPIC_MODEL_REASONING", "claude-opus-4-7"),
            ),
            ProviderStatus(
                provider="deepseek",
                configured=has_secret("DEEPSEEK_API_KEY"),
                default_model=os.getenv("DEEPSEEK_MODEL_DEFAULT", "deepseek-v4-flash"),
                fast_model=os.getenv("DEEPSEEK_MODEL_FAST", "deepseek-v4-flash"),
                reasoning_model=os.getenv("DEEPSEEK_MODEL_REASONING", "deepseek-v4-pro"),
            ),
            ProviderStatus(
                provider="openrouter",
                configured=has_secret("OPENROUTER_API_KEY"),
                default_model=os.getenv("OPENROUTER_MODEL_DEFAULT", "openrouter/auto"),
                fast_model=os.getenv("OPENROUTER_MODEL_FAST", "openrouter/auto"),
                reasoning_model=os.getenv("OPENROUTER_MODEL_REASONING", "openrouter/auto"),
            ),
        ]
        return {
            "project": os.getenv("PROJECT_NAME", "AstraCoreOS"),
            "environment": os.getenv("ENVIRONMENT", "development"),
            "paid_models_enabled": self.paid_models_enabled,
            "active_provider": self.model_provider,
            "max_paid_calls_per_day": self.max_paid_calls_per_day,
            "supabase_configured": has_secret("SUPABASE_URL") and has_secret("SUPABASE_ANON_KEY"),
            "google_oauth_configured": has_secret("GOOGLE_CLIENT_ID") and has_secret("GOOGLE_CLIENT_SECRET"),
            "github_repository": os.getenv("GITHUB_REPOSITORY", ""),
            "github_token_configured": has_secret("GITHUB_TOKEN"),
            "email_provider": os.getenv("EMAIL_PROVIDER", ""),
            "email_configured": (
                (os.getenv("EMAIL_PROVIDER", "").strip().lower() == "gmail" and has_secret("GMAIL_CLIENT_ID") and has_secret("GMAIL_CLIENT_SECRET"))
                or (os.getenv("EMAIL_PROVIDER", "").strip().lower() == "sendgrid" and has_secret("SENDGRID_API_KEY"))
            ),
            "providers": [provider.to_dict() for provider in providers],
        }
