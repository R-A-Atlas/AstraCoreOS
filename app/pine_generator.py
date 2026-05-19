from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import re
from pathlib import Path
from uuid import uuid4


@dataclass(frozen=True)
class PineStrategyArtifact:
    id: str
    title: str
    filename: str
    path: str
    summary: str
    created_at: str

    def to_dict(self) -> dict:
        return asdict(self)


class PineStrategyGenerator:
    def __init__(self, root: Path) -> None:
        self.output_dir = root / "workspace" / "outputs"

    def generate_scalp_assist(self, notes: str, name: str = "AstraCore Scalp Assist") -> PineStrategyArtifact:
        clean_name = self._clean_title(name)
        source_notes = self._comment_block(notes)
        pine = self._template(clean_name, source_notes)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        filename = self._safe_filename(clean_name)
        path = self.output_dir / filename
        path.write_text(pine, encoding="utf-8")
        return PineStrategyArtifact(
            id=str(uuid4()),
            title=clean_name,
            filename=filename,
            path=str(path),
            summary="Generated a Pine v6 scalp-assist strategy with clean entries, exits, visual markers, and alert messages.",
            created_at=datetime.now(timezone.utc).isoformat(),
        )

    @staticmethod
    def _clean_title(name: str) -> str:
        cleaned = re.sub(r"\s+", " ", (name or "").strip())
        return cleaned[:80] or "AstraCore Scalp Assist"

    @staticmethod
    def _safe_filename(title: str) -> str:
        slug = re.sub(r"[^a-zA-Z0-9]+", "-", title.lower()).strip("-")
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        return f"{slug or 'astracore-scalp-assist'}-{stamp}.pine"

    @staticmethod
    def _comment_block(notes: str) -> str:
        cleaned = (notes or "").strip()
        if not cleaned:
            cleaned = "No discretionary notes supplied yet. Use capture review to refine this strategy."
        lines = []
        for raw_line in cleaned.splitlines()[:24]:
            line = raw_line.strip()
            if line:
                lines.append(f"// {line[:140]}")
        return "\n".join(lines)

    @staticmethod
    def _template(title: str, source_notes: str) -> str:
        return f"""//@version=6
// @strategy_alert_message {{strategy.order.alert_message}}
strategy("{title}", overlay=true, pyramiding=0, initial_capital=50000, commission_type=strategy.commission.cash_per_contract, commission_value=2.0, slippage=1, margin_long=100, margin_short=100)

// Source notes captured from the trader:
{source_notes}

// Goal:
// Clean scalp-assist framework. It does not predict. It waits for trend context,
// a reclaim/reject trigger, volatility filter, and bar confirmation.

fastLen = input.int(9, "Fast EMA", minval=1)
slowLen = input.int(21, "Slow EMA", minval=1)
atrLen = input.int(14, "ATR Length", minval=1)
atrMin = input.float(8.0, "Minimum ATR", minval=0.0, step=0.25)
stopAtr = input.float(0.9, "Stop ATR", minval=0.1, step=0.1)
targetAtr = input.float(1.35, "Target ATR", minval=0.1, step=0.1)
showEma = input.bool(false, "Show EMAs")
allowLongs = input.bool(true, "Allow Longs")
allowShorts = input.bool(true, "Allow Shorts")
tradeSession = input.session("0930-1130,1330-1550", "Active Session")

inSession = not na(time(timeframe.period, tradeSession))
confirmed = barstate.isconfirmed
fastEma = ta.ema(close, fastLen)
slowEma = ta.ema(close, slowLen)
atr = ta.atr(atrLen)

trendUp = fastEma > slowEma and close > slowEma
trendDown = fastEma < slowEma and close < slowEma
volOk = atr >= atrMin

priorHigh = high[1]
priorLow = low[1]
reclaimLong = close > priorHigh and low <= priorHigh
rejectShort = close < priorLow and high >= priorLow

longSignal = allowLongs and inSession and confirmed and volOk and trendUp and reclaimLong and strategy.position_size == 0
shortSignal = allowShorts and inSession and confirmed and volOk and trendDown and rejectShort and strategy.position_size == 0

longStop = close - atr * stopAtr
longTarget = close + atr * targetAtr
shortStop = close + atr * stopAtr
shortTarget = close - atr * targetAtr

if longSignal
    strategy.entry("L", strategy.long, alert_message="ASTRACORE LONG {{ticker}} {{interval}} close={{close}}")
    strategy.exit("L-Exit", "L", stop=longStop, limit=longTarget, alert_message="ASTRACORE LONG EXIT {{ticker}} {{interval}} close={{close}}")
    alert("ASTRACORE LONG " + syminfo.ticker + " " + timeframe.period + " close=" + str.tostring(close), alert.freq_once_per_bar_close)

if shortSignal
    strategy.entry("S", strategy.short, alert_message="ASTRACORE SHORT {{ticker}} {{interval}} close={{close}}")
    strategy.exit("S-Exit", "S", stop=shortStop, limit=shortTarget, alert_message="ASTRACORE SHORT EXIT {{ticker}} {{interval}} close={{close}}")
    alert("ASTRACORE SHORT " + syminfo.ticker + " " + timeframe.period + " close=" + str.tostring(close), alert.freq_once_per_bar_close)

plot(showEma ? fastEma : na, "Fast EMA", color=color.new(color.teal, 0))
plot(showEma ? slowEma : na, "Slow EMA", color=color.new(color.orange, 0))
plotshape(longSignal, title="Long Setup", style=shape.triangleup, location=location.belowbar, size=size.tiny, color=color.lime, text="L")
plotshape(shortSignal, title="Short Setup", style=shape.triangledown, location=location.abovebar, size=size.tiny, color=color.red, text="S")
bgcolor(inSession ? na : color.new(color.gray, 94), title="Inactive Session Shade")
"""
