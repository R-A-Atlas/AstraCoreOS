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
        filename = self._safe_filename(clean_name, ".html")
        path = self.output_dir / filename
        path.write_text(brief, encoding="utf-8")
        return StrategyArtifact(
            id=str(uuid4()),
            title=clean_name,
            filename=filename,
            path=str(path),
            summary="Generated a visual HTML trading playbook from the capture transcript and strategy notes.",
            created_at=datetime.now(timezone.utc).isoformat(),
        )

    def write_custom_artifact(self, content: str, name: str, export_type: str, summary: str = "") -> StrategyArtifact:
        clean_name = self._clean_title(name)
        clean_export_type = export_type.strip().lower()
        suffix = {
            "pine": ".pine",
            "mt5": ".mq5",
            "mql5": ".mq5",
            "instructions": ".html",
            "brief": ".html",
            "markdown": ".html",
        }.get(clean_export_type)
        if suffix is None:
            raise ValueError("Unsupported export type.")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        filename = self._safe_filename(clean_name, suffix)
        path = self.output_dir / filename
        path.write_text(content, encoding="utf-8")
        return StrategyArtifact(
            id=str(uuid4()),
            title=clean_name,
            filename=filename,
            path=str(path),
            summary=summary or f"Generated {clean_export_type} export from AstraCore AI Brain.",
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
        escaped_title = PineStrategyGenerator._escape_html(title)
        escaped_notes = PineStrategyGenerator._escape_html(cleaned)
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{escaped_title} · Trade Playbook</title>
  <style>
    :root {{
      --bg: #080910;
      --panel: rgba(18, 20, 31, 0.86);
      --panel-2: rgba(255, 255, 255, 0.045);
      --line: rgba(255, 255, 255, 0.12);
      --text: #f6f7fb;
      --muted: #a7adbf;
      --brand: #a78bfa;
      --hot: #ff4f58;
      --good: #45f28a;
      --warn: #f9ca4d;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      min-height: 100vh;
      background:
        radial-gradient(circle at 12% 0%, rgba(167, 139, 250, 0.22), transparent 28rem),
        radial-gradient(circle at 86% 18%, rgba(255, 79, 88, 0.14), transparent 24rem),
        linear-gradient(135deg, #080910, #12111c 58%, #090a10);
      color: var(--text);
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      line-height: 1.55;
    }}
    main {{
      width: min(1120px, calc(100vw - 32px));
      margin: 0 auto;
      padding: 48px 0;
    }}
    header {{
      display: grid;
      gap: 18px;
      margin-bottom: 28px;
    }}
    .brand {{
      color: var(--brand);
      font-family: "JetBrains Mono", Consolas, monospace;
      font-size: 12px;
      letter-spacing: 0.16em;
      text-transform: uppercase;
    }}
    h1 {{
      margin: 0;
      max-width: 820px;
      font-size: clamp(42px, 7vw, 82px);
      line-height: 0.92;
      letter-spacing: -0.07em;
    }}
    .subtitle {{
      max-width: 720px;
      color: var(--muted);
      font-size: 18px;
    }}
    .grid {{
      display: grid;
      grid-template-columns: 1.15fr 0.85fr;
      gap: 18px;
      align-items: start;
    }}
    .card {{
      border: 1px solid var(--line);
      border-radius: 22px;
      background: var(--panel);
      box-shadow: 0 24px 70px rgba(0, 0, 0, 0.34);
      padding: 22px;
    }}
    .card h2 {{
      margin: 0 0 14px;
      font-size: 19px;
      letter-spacing: -0.03em;
    }}
    .steps {{
      display: grid;
      gap: 12px;
      counter-reset: step;
    }}
    .step {{
      counter-increment: step;
      display: grid;
      grid-template-columns: 42px 1fr;
      gap: 12px;
      align-items: start;
      padding: 14px;
      border: 1px solid var(--line);
      border-radius: 16px;
      background: var(--panel-2);
    }}
    .step::before {{
      content: counter(step);
      width: 34px;
      height: 34px;
      display: grid;
      place-items: center;
      border-radius: 50%;
      background: var(--brand);
      color: #0b0714;
      font-weight: 800;
    }}
    .chips {{
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      margin-top: 12px;
    }}
    .chip {{
      border: 1px solid var(--line);
      border-radius: 999px;
      padding: 7px 10px;
      color: var(--muted);
      background: rgba(255, 255, 255, 0.04);
      font-size: 13px;
    }}
    .transcript {{
      white-space: pre-wrap;
      color: #d9dcef;
      background: rgba(0, 0, 0, 0.26);
      border: 1px solid var(--line);
      border-radius: 16px;
      padding: 16px;
      max-height: 460px;
      overflow: auto;
    }}
    .rule {{
      display: grid;
      gap: 6px;
      padding: 14px 0;
      border-bottom: 1px solid var(--line);
    }}
    .rule:last-child {{ border-bottom: 0; }}
    .rule strong {{ color: var(--text); }}
    .rule span {{ color: var(--muted); }}
    .badge-row {{
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      margin-top: 20px;
    }}
    .badge {{
      border: 1px solid var(--line);
      border-radius: 14px;
      padding: 12px 14px;
      background: rgba(255, 255, 255, 0.05);
      min-width: 150px;
    }}
    .badge b {{
      display: block;
      color: var(--good);
      font-size: 20px;
    }}
    footer {{
      margin-top: 18px;
      color: var(--muted);
      font-size: 13px;
    }}
    @media (max-width: 880px) {{
      .grid {{ grid-template-columns: 1fr; }}
      main {{ padding: 28px 0; }}
    }}
  </style>
</head>
<body>
  <main>
    <header>
      <div class="brand">AstraCore Trade Playbook</div>
      <h1>{escaped_title}</h1>
      <p class="subtitle">A structured trading guide generated from your captured narration. Use it to refine your discretionary process into repeatable rules.</p>
      <div class="badge-row">
        <div class="badge"><b>01</b>Context first</div>
        <div class="badge"><b>02</b>Confirmation only</div>
        <div class="badge"><b>03</b>Defined invalidation</div>
      </div>
    </header>

    <section class="grid">
      <article class="card">
        <h2>Strategy Logic</h2>
        <div class="steps">
          <div class="step"><div><strong>Read the market context.</strong><br><span>Trend direction, active session, volatility, and nearby liquidity come before entry.</span></div></div>
          <div class="step"><div><strong>Wait for confirmation.</strong><br><span>Default long confirmation is reclaiming the prior candle high. Default short confirmation is rejecting below the prior candle low.</span></div></div>
          <div class="step"><div><strong>Align with trend.</strong><br><span>Do not force trades against the fast and slow trend unless your narration clearly defines a reversal setup.</span></div></div>
          <div class="step"><div><strong>Define invalidation before entry.</strong><br><span>The stop belongs beyond the trigger candle or the level that proves the idea wrong.</span></div></div>
          <div class="step"><div><strong>Target liquidity or a fixed multiple.</strong><br><span>Default target logic is nearest liquidity, prior high/low, or an ATR-based objective.</span></div></div>
        </div>
      </article>

      <aside class="card">
        <h2>Execution Checklist</h2>
        <div class="rule"><strong>Market and timeframe</strong><span>Confirm exactly what instrument and timeframe this applies to.</span></div>
        <div class="rule"><strong>Entry trigger</strong><span>What must happen before you are allowed to click buy or sell?</span></div>
        <div class="rule"><strong>Skip condition</strong><span>What makes the setup too late, too choppy, or invalid?</span></div>
        <div class="rule"><strong>Risk placement</strong><span>Where does the trade idea become wrong?</span></div>
        <div class="rule"><strong>First target</strong><span>Where is the nearest realistic liquidity or measured exit?</span></div>
        <div class="chips">
          <span class="chip">Scalp Assist</span>
          <span class="chip">Trader Narration</span>
          <span class="chip">Draft Rules</span>
        </div>
      </aside>

      <article class="card" style="grid-column: 1 / -1;">
        <h2>Source Transcript</h2>
        <div class="transcript">{escaped_notes}</div>
      </article>
    </section>

    <footer>This playbook is generated from your saved transcript. Chart-frame interpretation and full AI video review are the next system layer; verify the rules against the recording before using them live.</footer>
  </main>
</body>
</html>
"""

    @staticmethod
    def _escape_html(value: str) -> str:
        return (
            str(value)
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&#039;")
        )

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
