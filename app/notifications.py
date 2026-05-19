from __future__ import annotations

from dataclasses import asdict, dataclass
import os

from app.config import env_bool, has_secret


@dataclass(frozen=True)
class NotificationChannel:
    id: str
    title: str
    enabled: bool
    configured: bool
    status: str
    purpose: str

    def to_dict(self) -> dict:
        return asdict(self)


def notification_channels() -> list[NotificationChannel]:
    telegram_enabled = env_bool("TELEGRAM_ENABLED", False)
    telegram_configured = has_secret("TELEGRAM_BOT_TOKEN") and has_secret("TELEGRAM_CHAT_ID")

    email_provider = os.getenv("EMAIL_PROVIDER", "").strip().lower()
    email_enabled = env_bool("EMAIL_NOTIFICATIONS_ENABLED", False)
    gmail_configured = email_provider == "gmail" and has_secret("GMAIL_CLIENT_ID") and has_secret("GMAIL_CLIENT_SECRET")
    sendgrid_configured = email_provider == "sendgrid" and has_secret("SENDGRID_API_KEY")
    email_configured = has_secret("NOTIFICATION_EMAIL_TO") and (gmail_configured or sendgrid_configured)

    return [
        NotificationChannel(
            id="telegram",
            title="Telegram Updates",
            enabled=telegram_enabled,
            configured=telegram_configured,
            status=_channel_status(telegram_enabled, telegram_configured),
            purpose="Push market-prep, risk, and agent-task alerts to a private Telegram chat.",
        ),
        NotificationChannel(
            id="email",
            title="Email Updates",
            enabled=email_enabled,
            configured=email_configured,
            status=_channel_status(email_enabled, email_configured),
            purpose="Send daily briefs, reports, and completed agent artifacts by email.",
        ),
    ]


def _channel_status(enabled: bool, configured: bool) -> str:
    if enabled and configured:
        return "ready"
    if enabled and not configured:
        return "enabled_missing_credentials"
    if configured:
        return "configured_disabled"
    return "off"
