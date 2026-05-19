from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import re
from pathlib import Path
from uuid import uuid4


@dataclass(frozen=True)
class StrategyArtifact:
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

    def generate_scalp_assist(self, notes: str, name: str = "AstraCore Scalp Assist") -> StrategyArtifact:
        clean_name = self._clean_title(name)
        source_notes = self._comment_block(notes)
        pine = self._template(clean_name, source_notes)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        filename = self._safe_filename(clean_name)
        path = self.output_dir / filename
        path.write_text(pine, encoding="utf-8")
        return StrategyArtifact(
            id=str(uuid4()),
            title=clean_name,
            filename=filename,
            path=str(path),
            summary="Generated a Pine v6 scalp-assist strategy with clean entries, exits, visual markers, and alert messages.",
            created_at=datetime.now(timezone.utc).isoformat(),
        )

    def generate_mql5_expert(self, notes: str, name: str = "AstraCore Scalp Assist") -> StrategyArtifact:
        clean_name = self._clean_title(name)
        source_notes = self._mql_comment_block(notes)
        mql5 = self._mql5_template(clean_name, source_notes)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        filename = self._safe_filename(clean_name, ".mq5")
        path = self.output_dir / filename
        path.write_text(mql5, encoding="utf-8")
        return StrategyArtifact(
            id=str(uuid4()),
            title=clean_name,
            filename=filename,
            path=str(path),
            summary="Generated an MT5/MQL5 Expert Advisor starter with configurable EMA, ATR, risk, session, and alert logic.",
            created_at=datetime.now(timezone.utc).isoformat(),
        )

    def generate_instruction_brief(self, notes: str, name: str = "AstraCore Scalp Assist") -> StrategyArtifact:
        clean_name = self._clean_title(name)
        brief = self._instructions_template(clean_name, notes)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        filename = self._safe_filename(clean_name, ".md")
        path = self.output_dir / filename
        path.write_text(brief, encoding="utf-8")
        return StrategyArtifact(
            id=str(uuid4()),
            title=clean_name,
            filename=filename,
            path=str(path),
            summary="Generated plain-English trading instructions from the capture transcript and strategy notes.",
            created_at=datetime.now(timezone.utc).isoformat(),
        )

    @staticmethod
    def _clean_title(name: str) -> str:
        cleaned = re.sub(r"\s+", " ", (name or "").strip())
        return cleaned[:80] or "AstraCore Scalp Assist"

    @staticmethod
    def _safe_filename(title: str, suffix: str = ".pine") -> str:
        slug = re.sub(r"[^a-zA-Z0-9]+", "-", title.lower()).strip("-")
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        return f"{slug or 'astracore-scalp-assist'}-{stamp}{suffix}"

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
    def _mql_comment_block(notes: str) -> str:
        cleaned = (notes or "").strip()
        if not cleaned:
            cleaned = "No capture transcript supplied yet. Review and refine manually."
        lines = []
        for raw_line in cleaned.splitlines()[:24]:
            line = raw_line.strip()
            if line:
                lines.append(f"// {line[:140]}")
        return "\n".join(lines)

    @staticmethod
    def _instructions_template(title: str, notes: str) -> str:
        cleaned = (notes or "").strip() or "No transcript supplied."
        return f"""# {title}

## Source Transcript / Trader Narration

{cleaned}

## Strategy Logic Draft

1. Identify the market context first: trend direction, volatility, active session, and nearby liquidity.
2. Wait for confirmation instead of predicting. The default confirmation is a reclaim of the prior candle high for longs or a rejection below the prior candle low for shorts.
3. Trade only when the fast trend is aligned with the slow trend.
4. Avoid low-volatility chop and unclear range conditions.
5. Place the stop beyond the trigger candle or beyond the invalidation point described in the narration.
6. Target the nearest obvious liquidity, prior high/low, or a defined ATR multiple.
7. Skip the trade when the setup is late, extended, unclear, or contradicts the trader's spoken invalidation rule.

## Execution Checklist

- What is the market and timeframe?
- Where is liquidity?
- What must happen before entry?
- What invalidates the idea?
- Where is the stop?
- Where is the first target?
- Is the trade still clean after spread, volatility, and news risk?

## Notes

This brief is generated from the saved capture transcript. Chart-frame interpretation is the next system layer; confirm the visual rules against the recording before trading live.
"""

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

    @staticmethod
    def _mql5_template(title: str, source_notes: str) -> str:
        safe_title = re.sub(r"[^a-zA-Z0-9_]+", "_", title).strip("_") or "AstraCore_Scalp_Assist"
        return f"""//+------------------------------------------------------------------+
//| {title}.mq5
//| Generated by AstraCore Studio
//+------------------------------------------------------------------+
#property strict
#property description "AstraCore MT5 scalp-assist starter generated from trader narration."

{source_notes}

#include <Trade/Trade.mqh>

CTrade Trade;

input int FastEmaPeriod = 9;
input int SlowEmaPeriod = 21;
input int AtrPeriod = 14;
input double MinAtrPoints = 80.0;
input double StopAtr = 0.9;
input double TargetAtr = 1.35;
input double Lots = 0.10;
input bool AllowLongs = true;
input bool AllowShorts = true;
input int StartHour = 9;
input int EndHour = 16;

int fastHandle;
int slowHandle;
int atrHandle;
datetime lastBarTime = 0;

int OnInit()
{{
   fastHandle = iMA(_Symbol, _Period, FastEmaPeriod, 0, MODE_EMA, PRICE_CLOSE);
   slowHandle = iMA(_Symbol, _Period, SlowEmaPeriod, 0, MODE_EMA, PRICE_CLOSE);
   atrHandle = iATR(_Symbol, _Period, AtrPeriod);
   if (fastHandle == INVALID_HANDLE || slowHandle == INVALID_HANDLE || atrHandle == INVALID_HANDLE)
      return INIT_FAILED;
   return INIT_SUCCEEDED;
}}

void OnDeinit(const int reason)
{{
   IndicatorRelease(fastHandle);
   IndicatorRelease(slowHandle);
   IndicatorRelease(atrHandle);
}}

void OnTick()
{{
   datetime barTime = iTime(_Symbol, _Period, 0);
   if (barTime == lastBarTime)
      return;
   lastBarTime = barTime;

   MqlDateTime dt;
   TimeToStruct(TimeCurrent(), dt);
   if (dt.hour < StartHour || dt.hour >= EndHour)
      return;

   if (PositionsTotal() > 0)
      return;

   double fast[2], slow[2], atr[2];
   if (CopyBuffer(fastHandle, 0, 0, 2, fast) < 2) return;
   if (CopyBuffer(slowHandle, 0, 0, 2, slow) < 2) return;
   if (CopyBuffer(atrHandle, 0, 0, 2, atr) < 2) return;

   double close0 = iClose(_Symbol, _Period, 1);
   double high0 = iHigh(_Symbol, _Period, 1);
   double low0 = iLow(_Symbol, _Period, 1);
   double priorHigh = iHigh(_Symbol, _Period, 2);
   double priorLow = iLow(_Symbol, _Period, 2);
   double point = SymbolInfoDouble(_Symbol, SYMBOL_POINT);
   bool volOk = atr[1] / point >= MinAtrPoints;

   bool trendUp = fast[1] > slow[1] && close0 > slow[1];
   bool trendDown = fast[1] < slow[1] && close0 < slow[1];
   bool reclaimLong = close0 > priorHigh && low0 <= priorHigh;
   bool rejectShort = close0 < priorLow && high0 >= priorLow;

   if (AllowLongs && volOk && trendUp && reclaimLong)
   {{
      double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
      double stop = ask - atr[1] * StopAtr;
      double target = ask + atr[1] * TargetAtr;
      Trade.Buy(Lots, _Symbol, ask, stop, target, "{safe_title} long");
   }}

   if (AllowShorts && volOk && trendDown && rejectShort)
   {{
      double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
      double stop = bid + atr[1] * StopAtr;
      double target = bid - atr[1] * TargetAtr;
      Trade.Sell(Lots, _Symbol, bid, stop, target, "{safe_title} short");
   }}
}}
"""
