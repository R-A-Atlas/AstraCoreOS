# AstraCore Project Inventory

Last updated: 2026-05-20

## Project Identity

AstraCore is a local trading strategy development assistant.

The current product is focused on one core workflow:

1. Record a TradingView/chart screen.
2. Capture microphone narration while the trader explains the setup.
3. Save the video and transcript.
4. Manage old captures.
5. Generate strategy artifacts from the transcript.
6. Run AI coaching reviews on saved captures.
7. Build local trading memory from reviewed sessions.

The long-term goal is to become a personal trading coach and strategy memory system: a local command center that learns how the trader thinks, identifies repeated setups and mistakes, and turns screen recordings into cleaner rules, Pine Script, MT5/MQL5 code, and visual strategy playbooks.

## Current User-Facing App

### Landing Page

Routes:

- `/`

Purpose:

- Public entry page for AstraCore.
- Explains the capture-to-strategy workflow.
- Links to Studio and Capture Library.
- Uses truthful current product language only:
  - screen + mic capture
  - transcript sidecars
  - Pine v6 / MT5 / Visual Playbook
  - local capture memory
- Describes AI trade review and trading memory as the active product direction.

### Studio

Routes:

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
- Run AI review on a selected capture when enabled.
- Show AI coaching output:
  - trade grade
  - setup type
  - strengths
  - mistakes
  - timestamped notes
  - next practice focus
- Show Trading Memory pattern insight from reviewed sessions.

## Backend Capabilities

Main backend:

- `app/backend.py`
- FastAPI application.
- Serves Landing, Studio, and Capture Library pages.
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

AI review and trading memory:

- `app/ai_brain.py`
- Runs Gemini multimodal export generation and AI trade reviews.
- AI review requires selected video plus mic audio or transcript context.
- `app/trading_memory.py`
- Stores review JSON beside captures.
- Stores aggregate memory under `workspace/memory/trading_reviews.jsonl`.
- Produces common setups, repeated mistakes, best scoring setups, rules to keep, rules to avoid, and a coach summary.

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
- Gemini text client exists.
- Gemini multimodal AI export brain exists behind explicit `.env` flags.

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

The running AstraCore app is not connected to this Codex chat session or GPT-5.5 as its runtime AI brain.

What is true today:

- Codex is being used to build the app.
- The app itself is a local FastAPI/browser app.
- Studio quick exports still use deterministic Local Template generation.
- Capture Library exports can use a Gemini multimodal AI Brain when `ASTRA_AI_BRAIN_ENABLED=true`, `ASTRA_AI_EXPORTS_ENABLED=true`, and `GEMINI_API_KEY` is configured.
- Capture Library reviews can use the Gemini multimodal AI Brain when `ASTRA_AI_BRAIN_ENABLED=true`, `ASTRA_AI_REVIEWS_ENABLED=true`, and `GEMINI_API_KEY` is configured.
- AI export requires selected video plus mic audio or transcript context. Transcript-only AI strategy generation is intentionally blocked.
- AI review also requires selected video plus mic audio or transcript context.

What is not true yet:

- The app does not call this Codex chat session.
- The app does not yet send video frames to GPT-5.5 or Claude.
- The app now has a first-pass AI coaching review path.
- The app now stores local trading memory from AI reviews.
- It does not yet run live real-time chart observation while recording.

Recommended future model setup:

- Current AI export brain: Gemini multimodal video upload with `gemini-2.5-flash` by default.
- Possible later primary reviewer: OpenAI GPT-5.5 for hard reasoning, coding, strategy critique, and chart-frame analysis.
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

Trading review memory supports:

- `summary`
- `trade_grade`
- `setup_type`
- `strengths`
- `mistakes`
- `timestamped_notes`
- `strategy_rules`
- `next_practice_focus`
- `voice_summary`

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
- `GET /api/captures/{capture_id}/review`
- `POST /api/captures/{capture_id}/review`
- `GET /api/trading-memory/summary`

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

Landing:

- `web/landing.html`
- `web/landing.css`
- `web/live-scene.js`

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
49 passed
```

JavaScript syntax checks:

```powershell
node --check web\studio.js
node --check web\library.js
node --check web\live-scene.js
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
- Landing route
- Capture Library route
- recent tray link to library
- selected-capture export behavior
- export failure when capture has no transcript
- multimodal AI export guardrails
- AI review guardrails
- AI review metadata persistence
- trading memory aggregation
- AI export context from saved review and memory
- old dashboard files removed

## What Is Not Built Yet

These are not currently implemented:

- GPT-5.5/OpenAI brain integration.
- Claude Sonnet 4.6 reviewer integration.
- Separate video-frame extraction pipeline.
- Timestamped chart image analysis.
- Live voice Jarvis/orb.
- Real-time chart observation while recording.
- Deeper strategy learning across many sessions.
- Notion export.
- Obsidian vault export.
- AI-edited replay video with captions.
- TradingView Pine deployment automation.
- Broker execution.
- Live trading.
- Full backtesting engine.
- Real-time market data feed.

## Next Recommended Build

The next build should add the Jarvis voice/orb layer on top of stored coaching memory.

Recommended sequence:

1. Add a floating reactive AstraCore orb.
2. Add browser text-to-speech for saved review voice summaries.
3. Make the orb react to AI speech output.
4. Add push-to-talk or hold-to-talk chat about the selected capture.
5. Let the voice layer read from review memory and answer questions about repeated mistakes.

## Current Honest Status

AstraCore is currently a working local trading capture, strategy-export, AI review, and local trading-memory app.

It is not yet a live Jarvis-style trading companion, but it now has the first working AI coaching and local trading memory layer.

The foundation is now in place for that next layer:

- recording
- transcript capture
- capture library
- metadata memory
- export regeneration
- AI review persistence
- local trading memory summaries
- model/provider configuration awareness
- test coverage

The next major step is adding the voice/orb interaction layer on top of the saved coaching memory.
