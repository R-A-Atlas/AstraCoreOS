# AstraCore Project Inventory

Last updated: 2026-05-19

## Project Identity

AstraCore is a local trading strategy development assistant.

The current product is focused on one core workflow:

1. Record a TradingView/chart screen.
2. Capture microphone narration while the trader explains the setup.
3. Save the video and transcript.
4. Manage old captures.
5. Generate strategy artifacts from the transcript.

The long-term goal is to become a personal trading coach and strategy memory system: a local command center that learns how the trader thinks, identifies repeated setups and mistakes, and turns screen recordings into cleaner rules, Pine Script, MT5/MQL5 code, and visual strategy playbooks.

## Current User-Facing App

### Studio

Routes:

- `/`
- `/studio`

Purpose:

- Screen/window capture through the browser.
- Microphone capture.
- Browser speech recognition transcript capture.
- Live caption overlay while recording.
- Save recording as `.webm`.
- Save transcript as `.txt` sidecar when available.
- Generate quick exports from the latest saved transcript:
  - Pine Script
  - MT5/MQL5 Expert Advisor starter
  - Visual HTML Playbook
- Show a compact recent captures tray.
- Link to the full Capture Library.

Important current behavior:

- The Studio tray shows recent captures only.
- It intentionally does not manage the full archive.
- The export drawer can collapse so the display area gets larger.

### Capture Library

Route:

- `/library`

Purpose:

- View all saved recordings.
- Search captures.
- Select a capture.
- Preview the saved video.
- View and download the transcript.
- Rename the capture display name without physically renaming files.
- Delete a capture and its transcript.
- Regenerate exports from an old capture transcript:
  - Pine Script
  - MT5/MQL5
  - Visual HTML Playbook
- Show placeholder AI memory fields:
  - AI review status
  - setup type
  - trade grade

## Backend Capabilities

Main backend:

- `app/backend.py`
- FastAPI application.
- Serves Studio and Capture Library pages.
- Exposes config, capture, export, memory, skill, and TradingView endpoints.

Capture storage:

- `app/capture_studio.py`
- Stores capture videos and transcript sidecars under `workspace/captures`.
- Maintains a local JSONL metadata index.
- Supports loading old records with default metadata.
- Supports metadata updates, delete, transcript lookup, and export history.

Strategy export generation:

- `app/pine_generator.py`
- Generates:
  - `.pine` Pine Script v6 strategy starter
  - `.mq5` MT5/MQL5 Expert Advisor starter
  - `.html` visual trade playbook

TradingView integration:

- `app/tradingview.py`
- Provides webhook ingestion for TradingView alerts.
- Supports optional secret validation.
- Stores recent alerts locally.

Configuration:

- `app/config.py`
- Loads `.env`.
- Reports safe provider/config status without exposing secret values.

Model routing and model clients:

- `app/model_router.py`
- `app/model_clients.py`
- Cheap-first routing exists.
- Gemini client exists.
- Full AI trading brain is not implemented yet.

General assistant leftovers from earlier direction:

- `app/agents/business_documentation_agent.py`
- `app/tools/document_writer.py`
- These can still create business documentation and Word documents, but they are not the main trading-command-center workflow.

Intel/skill scaffolding:

- `app/intel_runner.py`
- `app/skills_registry.py`
- Provides local skill packets and trading-intel task descriptions.
- This is scaffolding for future agent-style automation.

Notifications status:

- `app/notifications.py`
- Reports Telegram/email configuration status without exposing secrets.
- Sending notifications is not the current main workflow.

## AI / Model Reality

The running AstraCore app is not currently connected to Codex or GPT-5.5 as its runtime AI brain.

What is true today:

- Codex is being used to build the app.
- The app itself is a local FastAPI/browser app.
- The app currently generates strategy exports mostly through deterministic local backend templates using saved transcripts.
- Gemini client support exists, but AI use is limited and not the full trading strategy brain.

What is not true yet:

- The app does not call this Codex chat session.
- The app does not yet send video frames to GPT-5.5 or Claude.
- The app does not yet perform full AI chart analysis.
- The app does not yet perform timestamped trade critique.
- The app does not yet learn across sessions in a deep model-driven way.

Recommended future model setup:

- Primary brain: OpenAI GPT-5.5 for hard reasoning, coding, strategy critique, and chart-frame analysis.
- Low-cost background model: GPT-5.4-mini or Gemini Flash for summaries, tags, and metadata.
- Optional reviewer: Claude Sonnet 4.6 for second-opinion critique and alternate strategy review.

## Capture Memory

Current memory is local file-based.

Capture files:

- Stored under `workspace/captures`.
- Video files are `.webm`.
- Transcript sidecars are `.txt`.
- Metadata index is JSONL.

Generated outputs:

- Stored under `workspace/outputs`.

Capture metadata currently supports:

- `display_name`
- `tags`
- `notes_summary`
- `last_exported_at`
- `generated_exports`
- `ai_review_status`
- `mistake_markers`
- `setup_type`
- `trade_grade`

This metadata is the foundation for the future AI memory layer.

## API Inventory

Primary app routes:

- `GET /`
- `GET /studio`
- `GET /library`

Health and config:

- `GET /health`
- `GET /api/config/status`

Operator and memory:

- `POST /api/operator`
- `GET /api/memory`

Capture management:

- `POST /api/captures`
- `GET /api/captures?limit=&offset=`
- `PATCH /api/captures/{capture_id}`
- `DELETE /api/captures/{capture_id}`
- `POST /api/captures/{capture_id}/export`

Strategy generation:

- `POST /api/strategies/pine`
- `POST /api/strategies/export`

Download/static file access:

- `GET /api/download/{filename}`
- `/outputs/{filename}`
- `/captures/{filename}`

TradingView:

- `GET /api/integrations/tradingview/status`
- `POST /api/integrations/tradingview/webhook`

Intel/skills:

- `GET /api/skills`
- `GET /api/intel/status`
- `POST /api/intel/run`

## Frontend Files

Studio:

- `web/studio.html`
- `web/studio.css`
- `web/studio.js`

Capture Library:

- `web/library.html`
- `web/library.css`
- `web/library.js`

Old dashboard files were removed so the local app no longer routes to the previous cluttered dashboard.

## Verification State

Current verified test suite:

```powershell
python -m pytest tests/ -q
```

Last verified result:

```text
32 passed
```

JavaScript syntax checks:

```powershell
node --check web\studio.js
node --check web\library.js
```

Current test coverage includes:

- local/cheap greeting behavior
- config status without leaking secrets
- paid model routing guardrails
- business document agent behavior
- TradingView webhook secret handling
- capture save/transcript sidecar behavior
- capture metadata defaults
- capture rename/delete
- capture export history
- Pine strategy generation
- MT5/MQL5 generation
- visual HTML playbook generation
- Studio route
- Capture Library route
- recent tray link to library
- selected-capture export behavior
- export failure when capture has no transcript
- old dashboard files removed

## What Is Not Built Yet

These are not currently implemented:

- GPT-5.5/OpenAI brain integration.
- Claude Sonnet 4.6 reviewer integration.
- AI video-frame extraction.
- Chart image analysis.
- Timestamped AI trade critique.
- Real strategy learning over multiple sessions.
- Automatic setup classification from video.
- Behavioral coaching based on repeated mistakes.
- Notion export.
- Obsidian vault export.
- AI-edited replay video with captions.
- TradingView Pine deployment automation.
- Broker execution.
- Live trading.
- Full backtesting engine.
- Real-time market data feed.

## Next Recommended Build

The next build should be the AI Brain layer.

Recommended sequence:

1. Add an `AI Brain` backend service.
2. Start with transcript-only AI review for a selected capture.
3. Store the AI review result back into capture metadata.
4. Add frame extraction from saved `.webm` files.
5. Send selected frames plus transcript to the AI brain.
6. Produce timestamped trade critique:
   - what the trader saw
   - what rule was implied
   - what was valid
   - what was early/late/unclear
   - what should become a strategy rule
7. Use the critique to improve Pine, MT5/MQL5, and Visual Playbook outputs.

## Current Honest Status

AstraCore is currently a working local trading capture and strategy-export app.

It is not yet a true AI trading coach.

The foundation is now in place for that next layer:

- recording
- transcript capture
- capture library
- metadata memory
- export regeneration
- model/provider configuration awareness
- test coverage

The next major step is connecting a real model-backed AI review service to the saved capture memory.
