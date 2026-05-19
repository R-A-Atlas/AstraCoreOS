from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
import os
from pathlib import Path
from typing import Any
from uuid import uuid4

from app.config import env_bool, has_secret


@dataclass(frozen=True)
class TradingViewAlert:
    id: str
    symbol: str
    timeframe: str
    action: str
    price: str
    message: str
    raw: dict[str, Any]
    received_at: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class TradingViewBridge:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.alerts_path = root / "workspace" / "integrations" / "tradingview_alerts.jsonl"

    def status(self) -> dict[str, Any]:
        public_url = os.getenv("TRADINGVIEW_WEBHOOK_PUBLIC_URL", "").strip()
        return {
            "enabled": env_bool("TRADINGVIEW_WEBHOOK_ENABLED", True),
            "secret_configured": has_secret("TRADINGVIEW_WEBHOOK_SECRET"),
            "public_url_configured": bool(public_url),
            "public_url": public_url,
            "local_url": "/api/integrations/tradingview/webhook",
            "latest_alerts": [alert.to_dict() for alert in self.recent_alerts(5)],
        }

    def ingest(self, payload: dict[str, Any]) -> TradingViewAlert:
        self._validate_secret(payload)
        alert = TradingViewAlert(
            id=str(uuid4()),
            symbol=str(payload.get("symbol") or payload.get("ticker") or payload.get("syminfo.ticker") or "UNKNOWN"),
            timeframe=str(payload.get("timeframe") or payload.get("interval") or ""),
            action=str(payload.get("action") or payload.get("side") or payload.get("signal") or "alert"),
            price=str(payload.get("price") or payload.get("close") or ""),
            message=str(payload.get("message") or payload.get("text") or payload.get("alert_message") or ""),
            raw={key: value for key, value in payload.items() if key != "secret"},
            received_at=datetime.now(timezone.utc).isoformat(),
        )
        self.alerts_path.parent.mkdir(parents=True, exist_ok=True)
        with self.alerts_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(alert.to_dict()) + "\n")
        return alert

    def recent_alerts(self, limit: int = 20) -> list[TradingViewAlert]:
        if not self.alerts_path.exists():
            return []
        rows: list[TradingViewAlert] = []
        with self.alerts_path.open("r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    rows.append(TradingViewAlert(**data))
                except (json.JSONDecodeError, TypeError):
                    continue
        return rows[-limit:]

    @staticmethod
    def example_alert_body() -> dict[str, str]:
        return {
            "secret": "same-value-as-TRADINGVIEW_WEBHOOK_SECRET",
            "symbol": "{{ticker}}",
            "timeframe": "{{interval}}",
            "price": "{{close}}",
            "action": "alert",
            "message": "{{strategy.order.alert_message}}",
        }

    @staticmethod
    def _validate_secret(payload: dict[str, Any]) -> None:
        expected_secret = os.getenv("TRADINGVIEW_WEBHOOK_SECRET", "").strip()
        if not expected_secret:
            return
        supplied_secret = str(payload.get("secret", "")).strip()
        if supplied_secret != expected_secret:
            raise PermissionError("Invalid TradingView webhook secret.")
