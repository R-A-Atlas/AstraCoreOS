# AstraCore OS

AstraCore OS is a fresh Agentic OS prototype: chat on the left, live artifacts on the right, and cheap local tools doing the work before any paid model is used.

## First principle

Do not spend model credits unless the task needs it.

The first version uses:

- local Python tools for files and deterministic tasks
- a simple operator agent for intent routing
- optional provider-router stubs for OpenAI, Gemini, Claude, and DeepSeek later
- real artifact creation, starting with `.docx`

## Run

```powershell
cd C:\Users\crist\Projects\AstraCoreOS
python -m uvicorn app.backend:app --host 127.0.0.1 --port 8010 --reload
```

Open:

```text
http://127.0.0.1:8010
```

## First test command

```text
Create a one-page business plan for a mobile detailing business and save it as a Word document.
```

Expected result:

- Operator replies in chat
- Right visor shows a document artifact
- A real `.docx` file is created in `workspace/outputs`
- Activity steps show tool routing and cost mode

## Architecture

```text
User directive
-> OperatorAgent
-> cheap local classifier
-> local tool when possible
-> optional model router only when needed
-> artifact + memory log
-> UI display card
```

## Current status

MVP slice 1:

- `OperatorAgent`
- local document writer
- one-page business plan generation
- web UI shell
- trading command center shell
- TradingView alert webhook receiver
- tests

Paid model usage:

- disabled by default
- planned behind explicit confirmation

## TradingView alerts

AstraCore can receive TradingView alert webhooks and show the latest alerts in the command center.

Local endpoint:

```text
http://127.0.0.1:8010/api/integrations/tradingview/webhook
```

Example alert body:

```json
{
  "secret": "same-value-as-TRADINGVIEW_WEBHOOK_SECRET",
  "symbol": "{{ticker}}",
  "timeframe": "{{interval}}",
  "price": "{{close}}",
  "action": "alert",
  "message": "{{strategy.order.alert_message}}"
}
```

For real TradingView cloud alerts, `127.0.0.1` is not reachable from TradingView. Use a deployed URL or a temporary tunnel later, then set `TRADINGVIEW_WEBHOOK_PUBLIC_URL` in `.env`.
