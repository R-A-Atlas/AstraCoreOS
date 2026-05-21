from pathlib import Path

from fastapi.testclient import TestClient

from app.backend import app
from app.ai_brain import MultimodalAIBrain
from app.capture_studio import CaptureStudio
from app.command_center import default_command_center_state
from app.config import AppConfig
from app.intel_runner import IntelRunner
from app.notifications import notification_channels
from app.operator_agent import OperatorAgent
from app.pine_generator import PineStrategyGenerator
from app.skills_registry import skill_catalog
from app.trading_memory import TradingMemory
from app.tradingview import TradingViewBridge


def test_mobile_detailing_docx_created(tmp_path: Path):
    agent = OperatorAgent(tmp_path)

    result = agent.run(
        "Create a one-page business plan for a mobile detailing business and save it as a Word document."
    )

    assert result.ok is True
    assert result.mode == "document"
    assert result.model["provider"] == "local"
    assert result.model["estimated_cost_usd"] == 0.0
    assert result.artifacts
    assert result.context_packets
    assert result.context_packets[0]["agent"] == "business_documentation_agent"
    path = Path(result.artifacts[0]["path"])
    assert path.exists()
    assert path.suffix == ".docx"


def test_greeting_is_local_and_cheap(tmp_path: Path):
    agent = OperatorAgent(tmp_path)

    result = agent.run("hey how are you")

    assert result.ok is True
    assert result.mode == "chat"
    assert result.message == "I'm good. What do you want to test first?"
    assert result.artifacts == []
    assert result.model["paid_call_allowed"] is False
    assert result.context_packets == []


def test_greeting_stays_local_even_when_gemini_enabled(tmp_path: Path):
    env = tmp_path / ".env"
    env.write_text(
        "GEMINI_API_KEY=fake-key\n"
        "ASTRA_MODEL_PROVIDER=gemini\n"
        "ENABLE_PAID_MODELS=true\n"
        "ASTRA_MAX_PAID_CALLS_PER_DAY=5\n",
        encoding="utf-8",
    )
    agent = OperatorAgent(tmp_path)

    result = agent.run("hey how are you")

    assert result.model["provider"] == "local"
    assert result.model["paid_call_allowed"] is False


def test_capability_question_is_plain_text(tmp_path: Path):
    agent = OperatorAgent(tmp_path)

    result = agent.run("what can you do?")

    assert result.ok is True
    assert result.mode == "chat"
    assert "Business Documentation Agent" in result.message
    assert result.artifacts == []


def test_business_documentation_agent_handles_multiple_business_prompts(tmp_path: Path):
    agent = OperatorAgent(tmp_path)
    prompts = [
        ("Make a simple SOP for a cleaning business as a Word document.", "sop", "cleaning business"),
        ("Write a proposal for a local web design service and save it as a docx file.", "proposal", "local web design service"),
        ("Create a one-page finance report for a small bakery in a Word document.", "finance_report", "small bakery"),
    ]

    for prompt, expected_type, expected_business in prompts:
        result = agent.run(prompt)
        packet = result.context_packets[0]

        assert result.ok is True
        assert result.mode == "document"
        assert result.artifacts
        assert packet["data"]["document_type"] == expected_type
        assert packet["data"]["business"] == expected_business
        assert Path(result.artifacts[0]["path"]).exists()


def test_business_documentation_packet_without_file_when_no_document_requested(tmp_path: Path):
    agent = OperatorAgent(tmp_path)

    result = agent.run("Make a simple proposal for a local web design service business.")

    assert result.ok is True
    assert result.mode == "agent_packet"
    assert result.artifacts == []
    assert result.context_packets[0]["data"]["document_type"] == "proposal"


def test_business_documentation_memory_can_be_read_back(tmp_path: Path):
    agent = OperatorAgent(tmp_path)

    agent.run("Make a simple SOP for a cleaning business as a Word document.")
    memory = agent.recent_memory()

    assert len(memory) == 1
    assert "cleaning business" in memory[0]["directive"]
    assert memory[0]["context_packets"][0]["agent"] == "business_documentation_agent"
    assert memory[0]["artifact_path"].endswith(".docx")


def test_config_status_does_not_expose_secret_values(tmp_path: Path):
    env = tmp_path / ".env"
    env.write_text(
        "GEMINI_API_KEY=real-secret\n"
        "SUPABASE_URL=https://example.supabase.co\n"
        "SUPABASE_ANON_KEY=anon-secret\n",
        encoding="utf-8",
    )

    status = AppConfig(tmp_path).safe_status()

    assert status["providers"][0]["provider"] == "gemini"
    assert status["providers"][0]["configured"] is True
    assert "real-secret" not in str(status)
    assert status["supabase_configured"] is True


def test_ai_brain_config_defaults_are_safe_and_keyless(tmp_path: Path, monkeypatch):
    for key in [
        "ASTRA_AI_BRAIN_ENABLED",
        "ASTRA_AI_EXPORTS_ENABLED",
        "ASTRA_AI_BRAIN_PROVIDER",
        "ASTRA_AI_REVIEWS_ENABLED",
        "ASTRA_AI_REQUIRE_VIDEO",
        "ASTRA_AI_REQUIRE_AUDIO_OR_TRANSCRIPT",
        "ASTRA_AI_FALLBACK_TO_LOCAL",
        "GEMINI_API_KEY",
        "GEMINI_API_BASE_URL",
        "GEMINI_FILES_UPLOAD_URL",
        "GEMINI_MODEL_MULTIMODAL",
        "GEMINI_MODEL_MULTIMODAL_REASONING",
    ]:
        monkeypatch.delenv(key, raising=False)

    status = AppConfig(tmp_path).safe_status()

    assert status["ai_brain"]["enabled"] is False
    assert status["ai_brain"]["exports_enabled"] is False
    assert status["ai_brain"]["reviews_enabled"] is False
    assert status["ai_brain"]["provider"] == "gemini"
    assert status["ai_brain"]["require_video"] is True
    assert status["ai_brain"]["require_audio_or_transcript"] is True
    assert status["ai_brain"]["fallback_to_local"] is False
    assert status["ai_brain"]["gemini_configured"] is False
    assert status["ai_brain"]["gemini_api_base_url"] == "https://generativelanguage.googleapis.com"
    assert status["ai_brain"]["gemini_files_upload_url"] == "https://generativelanguage.googleapis.com/upload/v1beta/files"
    assert status["ai_brain"]["gemini_multimodal_model"] == "gemini-2.5-flash"
    assert status["ai_brain"]["gemini_multimodal_reasoning_model"] == "gemini-2.5-pro"


def test_paid_models_stay_local_when_disabled(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "fake-key")
    monkeypatch.setenv("ASTRA_MODEL_PROVIDER", "gemini")
    monkeypatch.setenv("ENABLE_PAID_MODELS", "false")
    monkeypatch.setenv("ASTRA_MAX_PAID_CALLS_PER_DAY", "10")
    agent = OperatorAgent(tmp_path)

    result = agent.run("Make a simple proposal for a local web design service business.")

    assert result.model["provider"] == "local"
    assert result.model["paid_call_allowed"] is False


def test_general_prompt_routes_to_general_model_when_enabled(tmp_path: Path):
    env = tmp_path / ".env"
    env.write_text(
        "GEMINI_API_KEY=fake-key\n"
        "ASTRA_MODEL_PROVIDER=gemini\n"
        "ENABLE_PAID_MODELS=true\n"
        "ASTRA_MAX_PAID_CALLS_PER_DAY=5\n",
        encoding="utf-8",
    )
    agent = OperatorAgent(tmp_path)

    result = agent.run("was just wondering what happened yesterday in the markets with NQ")

    assert result.mode == "chat"
    assert result.model["provider"] == "gemini"
    assert result.model["paid_call_allowed"] is True
    assert result.artifacts == []
    assert result.context_packets == []


def test_default_command_center_state_is_trading_focused():
    state = default_command_center_state().to_dict()

    assert state["title"] == "AstraCore Trading Command Center"
    assert "NQ" in state["market_prep"]["focus"]
    assert state["agent_tasks"][0]["owner"] == "Codex"
    assert state["agent_tasks"][1]["owner"] == "Claude Code"
    assert any(task["skill_id"] == "daily_market_prep" for task in state["intel_tasks"])
    assert any(channel["id"] == "telegram" for channel in state["notification_channels"])
    assert state["integrations"][0]["id"] == "tradingview"
    assert state["tradingview_alerts"] == []


def test_skill_catalog_registers_trading_intel_prompts():
    catalog = skill_catalog()
    skill_ids = {skill["id"] for skill in catalog["skills"]}

    assert catalog["domain"] == "trading_command_center"
    assert "daily_market_prep" in skill_ids
    assert "risk_check" in skill_ids
    assert "journal_review" in skill_ids
    assert all(skill["prompt_template"] for skill in catalog["skills"])


def test_notification_status_does_not_expose_secret_values(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("TELEGRAM_ENABLED", "true")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "telegram-secret")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "chat-secret")
    monkeypatch.setenv("EMAIL_PROVIDER", "sendgrid")
    monkeypatch.setenv("SENDGRID_API_KEY", "sendgrid-secret")
    monkeypatch.setenv("NOTIFICATION_EMAIL_TO", "test@example.com")

    channels = [channel.to_dict() for channel in notification_channels()]

    assert channels[0]["id"] == "telegram"
    assert channels[0]["status"] == "ready"
    assert channels[1]["id"] == "email"
    assert channels[1]["configured"] is True
    assert "telegram-secret" not in str(channels)
    assert "sendgrid-secret" not in str(channels)


def test_intel_runner_creates_skill_packet():
    result = IntelRunner().run("daily_market_prep", "prep NQ before the open")
    packet = result.packet

    assert result.ok is True
    assert result.skill_id == "daily_market_prep"
    assert packet["agent"] == "trading_intel_skill_runner"
    assert packet["data"]["skill_id"] == "daily_market_prep"
    assert "market_data" in result.missing_tools


def test_intel_runner_rejects_unknown_skill():
    result = IntelRunner().run("missing_skill")

    assert result.ok is False
    assert result.packet == {}
    assert "Unknown intel skill" in result.message


def test_tradingview_bridge_ingests_alert_without_exposing_secret(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("TRADINGVIEW_WEBHOOK_SECRET", "tv-secret")
    bridge = TradingViewBridge(tmp_path)

    alert = bridge.ingest(
        {
            "secret": "tv-secret",
            "symbol": "NQ1!",
            "timeframe": "5",
            "price": "21850.25",
            "action": "long_watch",
            "message": "NQ reclaim alert",
        }
    )
    recent = bridge.recent_alerts()
    status = bridge.status()

    assert alert.symbol == "NQ1!"
    assert recent[-1].action == "long_watch"
    assert status["secret_configured"] is True
    assert "tv-secret" not in str(alert.to_dict())
    assert "tv-secret" not in str(status)


def test_tradingview_bridge_rejects_bad_secret(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("TRADINGVIEW_WEBHOOK_SECRET", "tv-secret")
    bridge = TradingViewBridge(tmp_path)

    try:
        bridge.ingest({"secret": "wrong", "symbol": "NQ1!"})
    except PermissionError as exc:
        assert "Invalid TradingView" in str(exc)
    else:
        raise AssertionError("Expected bad TradingView secret to be rejected.")


def test_capture_studio_saves_webm_capture(tmp_path: Path):
    studio = CaptureStudio(tmp_path)

    session = studio.save_capture(b"fake-webm-data", "my screen review.webm")
    recent = studio.recent_captures()

    assert session.filename.endswith(".webm")
    assert " " not in session.filename
    assert Path(session.path).exists()
    assert recent[-1].id == session.id
    assert recent[-1].transcript_status == "pending"
    assert session.mic_enabled is False
    assert session.has_transcript is False
    assert session.ready_for_ai is False


def test_capture_studio_saves_transcript_sidecar(tmp_path: Path):
    studio = CaptureStudio(tmp_path)

    session = studio.save_capture(
        b"fake-webm-data",
        "my narrated review.webm",
        "I would enter after reclaiming the prior candle high.",
    )
    transcript_path = Path(session.transcript_path)

    assert session.transcript_status == "complete"
    assert session.transcript_filename.endswith(".txt")
    assert transcript_path.exists()
    assert session.has_transcript is True
    assert session.ready_for_ai is True
    assert "reclaiming the prior candle high" in transcript_path.read_text(encoding="utf-8")
    assert "reclaiming the prior candle high" in studio.latest_transcript()


def test_capture_studio_marks_mic_recordings_ready_for_ai(tmp_path: Path):
    studio = CaptureStudio(tmp_path)

    session = studio.save_capture(b"fake-webm-data", "mic-review.webm", mic_enabled=True)

    assert session.mic_enabled is True
    assert session.has_transcript is False
    assert session.ready_for_ai is True


def test_capture_studio_loads_old_records_with_metadata_defaults(tmp_path: Path):
    studio = CaptureStudio(tmp_path)
    studio.capture_dir.mkdir(parents=True, exist_ok=True)
    path = studio.capture_dir / "old-capture.webm"
    path.write_bytes(b"fake-webm-data")
    studio.index_path.write_text(
        '{"id":"old-1","filename":"old-capture.webm","path":"'
        + str(path).replace("\\", "\\\\")
        + '","size_bytes":14,"created_at":"2026-05-19T00:00:00+00:00","transcript_status":"pending","analysis_status":"pending"}\n',
        encoding="utf-8",
    )

    session = studio.all_captures()[0]

    assert session.display_name == "old-capture"
    assert session.generated_exports == []
    assert session.ai_review_status == "not_started"


def test_capture_studio_updates_and_deletes_capture_metadata(tmp_path: Path):
    studio = CaptureStudio(tmp_path)
    session = studio.save_capture(b"fake-webm-data", "review.webm", "Long after reclaim.")

    updated = studio.update_capture(session.id, display_name="Morning NQ reclaim", tags=["NQ", "scalp!"])

    assert updated.display_name == "Morning NQ reclaim"
    assert updated.tags == ["NQ", "scalp"]
    assert studio.get_capture(session.id).display_name == "Morning NQ reclaim"

    deleted = studio.delete_capture(session.id)

    assert deleted.id == session.id
    assert studio.get_capture(session.id) is None
    assert not Path(session.path).exists()
    assert not Path(session.transcript_path).exists()


def test_capture_studio_records_export_history(tmp_path: Path):
    studio = CaptureStudio(tmp_path)
    generator = PineStrategyGenerator(tmp_path)
    session = studio.save_capture(b"fake-webm-data", "review.webm", "Long after reclaim.")
    artifact = generator.generate_instruction_brief(studio.transcript_for(session.id), "Morning NQ")

    updated = studio.record_export(session.id, "instructions", artifact)

    assert updated.last_exported_at
    assert updated.generated_exports[-1]["filename"] == artifact.filename
    assert updated.generated_exports[-1]["type"] == "instructions"
    assert updated.generated_exports[-1]["source"] == "local_template"


def test_pine_generator_creates_clean_strategy_file(tmp_path: Path):
    generator = PineStrategyGenerator(tmp_path)

    artifact = generator.generate_scalp_assist(
        "I want NQ scalp entries after reclaiming prior candle high with trend behind me.",
        "My NQ Scalp",
    )
    path = Path(artifact.path)
    content = path.read_text(encoding="utf-8")

    assert path.exists()
    assert path.suffix == ".pine"
    assert "//@version=6" in content
    assert "strategy.entry" in content
    assert "alert(" in content
    assert "plotshape" in content


def test_strategy_generator_creates_mt5_and_instruction_exports(tmp_path: Path):
    generator = PineStrategyGenerator(tmp_path)
    notes = "NQ scalp long after reclaiming prior candle high. Stop under trigger candle."

    mt5 = generator.generate_mql5_expert(notes, "My NQ Scalp")
    instructions = generator.generate_instruction_brief(notes, "My NQ Scalp")
    mt5_content = Path(mt5.path).read_text(encoding="utf-8")
    instructions_content = Path(instructions.path).read_text(encoding="utf-8")

    assert mt5.filename.endswith(".mq5")
    assert "#include <Trade/Trade.mqh>" in mt5_content
    assert "Trade.Buy" in mt5_content
    assert instructions.filename.endswith(".html")
    assert "Execution Checklist" in instructions_content
    assert "AstraCore Trade Playbook" in instructions_content
    assert "reclaiming prior candle high" in instructions_content


def test_ai_brain_exports_from_saved_review_without_video_upload(tmp_path: Path, monkeypatch):
    class FakeVideoClient:
        model = "gemini-test"

        @property
        def configured(self) -> bool:
            return True

        def generate_from_video(self, video_path: Path, prompt: str) -> str:
            raise AssertionError("Exports should use saved review, not upload video again.")

    class FakeTextClient:
        model = "gemini-text-test"

        @property
        def configured(self) -> bool:
            return True

        def generate(self, prompt: str) -> str:
            assert "saved multimodal AI review" in prompt
            assert "Range reclaim" in prompt
            assert "I would enter after reclaiming" in prompt
            return (
                '{"title":"AI NQ Reclaim","summary":"Generated from video plus narration.",'
                '"exports":{"pine":"//@version=6\\nstrategy(\\"AI NQ Reclaim\\", overlay=true)\\n"}}'
            )

    monkeypatch.setenv("ASTRA_AI_BRAIN_ENABLED", "true")
    monkeypatch.setenv("ASTRA_AI_EXPORTS_ENABLED", "true")
    monkeypatch.setenv("ASTRA_AI_BRAIN_PROVIDER", "gemini")
    monkeypatch.setenv("GEMINI_API_KEY", "fake-key")
    studio = CaptureStudio(tmp_path)
    session = studio.save_capture(
        b"fake-webm-data",
        "nq-review.webm",
        "I would enter after reclaiming the range high.",
        mic_enabled=True,
    )
    generator = PineStrategyGenerator(tmp_path)
    brain = MultimodalAIBrain(tmp_path, generator, client=FakeVideoClient(), text_client=FakeTextClient())
    review = {"summary": "Saved review.", "setup_type": "Range reclaim", "strategy_rules": ["Long after reclaim."]}

    result = brain.generate_export(session, studio.transcript_for(session.id), "AI NQ Reclaim", "pine", review, {"total_reviews": 1})
    content = Path(result.artifact.path).read_text(encoding="utf-8")

    assert result.source == "ai_review_memory"
    assert result.model == "gemini-text-test"
    assert result.artifact.filename.endswith(".pine")
    assert "//@version=6" in content


def test_ai_brain_export_requires_saved_review(tmp_path: Path, monkeypatch):
    class FakeTextClient:
        model = "gemini-text-test"

        @property
        def configured(self) -> bool:
            return True

        def generate(self, prompt: str) -> str:
            raise AssertionError("AI text export should not run without saved review.")

    monkeypatch.setenv("ASTRA_AI_BRAIN_ENABLED", "true")
    monkeypatch.setenv("ASTRA_AI_EXPORTS_ENABLED", "true")
    monkeypatch.setenv("ASTRA_AI_BRAIN_PROVIDER", "gemini")
    monkeypatch.setenv("GEMINI_API_KEY", "fake-key")
    studio = CaptureStudio(tmp_path)
    session = studio.save_capture(b"fake-webm-data", "nq-review.webm", "Transcript only.", mic_enabled=True)
    brain = MultimodalAIBrain(tmp_path, PineStrategyGenerator(tmp_path), text_client=FakeTextClient())

    try:
        brain.generate_export(session, studio.transcript_for(session.id), "Bad Export", "pine")
    except RuntimeError as exc:
        assert str(exc) == "Run AI Review before AI export."
    else:
        raise AssertionError("Expected missing review to block AI export.")


def test_ai_brain_export_missing_key_fails_after_review_exists(tmp_path: Path, monkeypatch):
    class FakeTextClient:
        model = "gemini-text-test"

        @property
        def configured(self) -> bool:
            return False

        def generate(self, prompt: str) -> str:
            raise AssertionError("AI text export should not run without key.")

    monkeypatch.setenv("ASTRA_AI_BRAIN_ENABLED", "true")
    monkeypatch.setenv("ASTRA_AI_EXPORTS_ENABLED", "true")
    monkeypatch.setenv("ASTRA_AI_BRAIN_PROVIDER", "gemini")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    studio = CaptureStudio(tmp_path)
    session = studio.save_capture(b"fake-webm-data", "silent.webm", "Transcript.", mic_enabled=True)
    brain = MultimodalAIBrain(tmp_path, PineStrategyGenerator(tmp_path), text_client=FakeTextClient())
    review = {"summary": "Saved review.", "setup_type": "Range reclaim"}

    try:
        brain.generate_export(session, "Transcript.", "Silent Export", "pine", review)
    except RuntimeError as exc:
        assert str(exc) == "Gemini API key missing."
    else:
        raise AssertionError("Expected missing Gemini key to block AI export.")


def test_multimodal_ai_brain_generates_trading_review(tmp_path: Path, monkeypatch):
    class FakeGeminiClient:
        model = "gemini-review-test"

        @property
        def configured(self) -> bool:
            return True

        def generate_from_video(self, video_path: Path, prompt: str) -> str:
            assert video_path.exists()
            assert "direct trading coach" in prompt
            assert "Existing trading memory summary" in prompt
            return (
                '{"summary":"You waited for confirmation but entered slightly late.",'
                '"trade_grade":"B","setup_type":"Range reclaim",'
                '"strengths":["Waited for reclaim"],'
                '"mistakes":["Entry came after the best impulse"],'
                '"timestamped_notes":[{"timecode":"01:12","label":"Entry timing",'
                '"observation":"Price had already expanded from the range high.",'
                '"coaching_note":"Enter closer to reclaim or skip.","severity":"high"}],'
                '"strategy_rules":["Long only after reclaim holds"],'
                '"next_practice_focus":"Practice entering closer to the reclaim.",'
                '"voice_summary":"Good read, but tighten the entry timing."}'
            )

    monkeypatch.setenv("ASTRA_AI_BRAIN_ENABLED", "true")
    monkeypatch.setenv("ASTRA_AI_REVIEWS_ENABLED", "true")
    monkeypatch.setenv("ASTRA_AI_BRAIN_PROVIDER", "gemini")
    monkeypatch.setenv("GEMINI_API_KEY", "fake-key")
    studio = CaptureStudio(tmp_path)
    session = studio.save_capture(b"fake-webm-data", "review.webm", "I waited for reclaim.", mic_enabled=True)
    brain = MultimodalAIBrain(tmp_path, PineStrategyGenerator(tmp_path), client=FakeGeminiClient())

    review = brain.generate_review(session, studio.transcript_for(session.id), {"total_reviews": 0})

    assert review["source"] == "ai_multimodal_review"
    assert review["model"] == "gemini-review-test"
    assert review["trade_grade"] == "B"
    assert review["setup_type"] == "Range reclaim"
    assert review["timestamped_notes"][0]["timecode"] == "01:12"


def test_trading_memory_saves_review_and_aggregates_summary(tmp_path: Path):
    studio = CaptureStudio(tmp_path)
    memory = TradingMemory(tmp_path)
    first = studio.save_capture(b"fake-webm-data", "first.webm", "First.", mic_enabled=True)
    second = studio.save_capture(b"fake-webm-data", "second.webm", "Second.", mic_enabled=True)

    memory.save_review(
        first,
        {
            "summary": "Good reclaim.",
            "trade_grade": "A",
            "setup_type": "Range reclaim",
            "mistakes": ["Chased entry"],
            "strategy_rules": ["Wait for reclaim"],
            "timestamped_notes": [{"timecode": "00:30", "label": "Chase", "coaching_note": "Do not chase.", "severity": "high"}],
        },
    )
    memory.save_review(
        second,
        {
            "summary": "Late entry.",
            "trade_grade": "C",
            "setup_type": "Range reclaim",
            "mistakes": ["Chased entry"],
            "strategy_rules": ["Wait for reclaim"],
        },
    )
    summary = memory.summary()

    assert summary["total_reviews"] == 2
    assert summary["common_setups"][0]["setup_type"] == "Range reclaim"
    assert summary["repeated_mistakes"][0]["mistake"] == "Chased entry"
    assert summary["rules_to_keep"][0]["rule"] == "Wait for reclaim"
    assert "Range reclaim" in summary["coach_summary"]


def test_strategy_export_uses_latest_capture_transcript_when_notes_empty(tmp_path: Path):
    studio = CaptureStudio(tmp_path)
    generator = PineStrategyGenerator(tmp_path)
    studio.save_capture(
        b"fake-webm-data",
        "capture.webm",
        "Long only after reclaiming prior candle high with trend behind me.",
    )

    artifact = generator.generate_instruction_brief(studio.latest_transcript(), "Transcript Strategy")
    content = Path(artifact.path).read_text(encoding="utf-8")

    assert "Long only after reclaiming prior candle high" in content


def test_studio_route_serves_focused_capture_ui():
    client = TestClient(app)

    response = client.get("/studio")

    assert response.status_code == 200
    assert "AstraCore Studio" in response.text
    assert "Connect a chart display" in response.text
    assert "Walkthrough guide" in response.text
    assert "range high, range low" in response.text
    assert 'href="/"' in response.text
    assert "AI coach standing by" in response.text
    assert "/static/studio.js" in response.text


def test_root_route_serves_landing_page():
    client = TestClient(app)

    root_response = client.get("/")

    assert root_response.status_code == 200
    assert "AstraCore - Trading Strategy Capture" in root_response.text
    assert "Record your chart, explain your read" in root_response.text
    assert "/static/landing.css" in root_response.text
    assert "/static/live-scene.js" in root_response.text
    assert 'href="/studio"' in root_response.text
    assert 'href="/library"' in root_response.text
    assert "/static/studio.js" not in root_response.text
    assert "AstraCore Trading Command Center" not in root_response.text
    assert "/static/app.js" not in root_response.text
    assert root_response.headers["cache-control"] == "no-store"


def test_library_route_serves_capture_library():
    client = TestClient(app)

    response = client.get("/library")

    assert response.status_code == 200
    assert "AstraCore Capture Library" in response.text
    assert "/static/library.js" in response.text
    assert "Run AI Review" in response.text
    assert "Pattern insight" in response.text
    assert 'href="/"' in response.text
    assert 'href="/studio"' in response.text
    assert "AI coach standing by" in response.text


def test_studio_recent_tray_links_to_library():
    client = TestClient(app)

    response = client.get("/studio")

    assert response.status_code == 200
    assert "View all captures" in response.text
    assert 'href="/library"' in response.text


def test_capture_api_limit_rename_delete_and_selected_export(tmp_path: Path, monkeypatch):
    test_studio = CaptureStudio(tmp_path)
    test_generator = PineStrategyGenerator(tmp_path)
    monkeypatch.setattr("app.backend.capture_studio", test_studio)
    monkeypatch.setattr("app.backend.pine_generator", test_generator)
    client = TestClient(app)

    first = test_studio.save_capture(b"fake-webm-data", "first.webm", "First transcript.")
    second = test_studio.save_capture(b"fake-webm-data", "second.webm", "Second transcript reclaiming high.")
    test_studio.save_capture(b"fake-webm-data", "third.webm", "Third transcript.")
    test_studio.save_capture(b"fake-webm-data", "fourth.webm", "Fourth transcript.")
    test_studio.save_capture(b"fake-webm-data", "fifth.webm", "Fifth transcript.")

    limited = client.get("/api/captures?limit=4")
    payload = limited.json()

    assert limited.status_code == 200
    assert len(payload["captures"]) == 4
    assert payload["total"] == 5
    assert payload["captures"][0]["id"] != first.id

    renamed = client.patch(f"/api/captures/{second.id}", json={"display_name": "NQ reclaim review"})
    assert renamed.status_code == 200
    assert renamed.json()["capture"]["display_name"] == "NQ reclaim review"

    exported = client.post(
        f"/api/captures/{second.id}/export",
        json={"name": "NQ reclaim review", "export_type": "instructions", "export_mode": "local"},
    )
    export_payload = exported.json()

    assert exported.status_code == 200
    assert export_payload["strategy"]["source"] == "local_template"
    assert export_payload["strategy"]["download_url"].endswith(".html")
    assert export_payload["capture"]["generated_exports"][-1]["type"] == "instructions"
    assert export_payload["capture"]["generated_exports"][-1]["source"] == "local_template"

    deleted = client.delete(f"/api/captures/{second.id}")

    assert deleted.status_code == 200
    assert test_studio.get_capture(second.id) is None


def test_capture_ai_export_disabled_fails_cleanly(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("ASTRA_AI_BRAIN_ENABLED", "false")
    monkeypatch.setenv("ASTRA_AI_EXPORTS_ENABLED", "false")
    test_studio = CaptureStudio(tmp_path)
    test_generator = PineStrategyGenerator(tmp_path)
    monkeypatch.setattr("app.backend.capture_studio", test_studio)
    monkeypatch.setattr("app.backend.ai_brain", MultimodalAIBrain(tmp_path, test_generator))
    client = TestClient(app)
    session = test_studio.save_capture(
        b"fake-webm-data",
        "review.webm",
        "Long after reclaim.",
        mic_enabled=True,
    )

    response = client.post(
        f"/api/captures/{session.id}/export",
        json={"name": "AI disabled", "export_type": "pine", "export_mode": "ai"},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "AI Brain disabled."


def test_capture_ai_export_missing_gemini_key_fails_cleanly(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("ASTRA_AI_BRAIN_ENABLED", "true")
    monkeypatch.setenv("ASTRA_AI_EXPORTS_ENABLED", "true")
    monkeypatch.setenv("ASTRA_AI_BRAIN_PROVIDER", "gemini")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    test_studio = CaptureStudio(tmp_path)
    test_generator = PineStrategyGenerator(tmp_path)
    monkeypatch.setattr("app.backend.capture_studio", test_studio)
    monkeypatch.setattr("app.backend.ai_brain", MultimodalAIBrain(tmp_path, test_generator))
    client = TestClient(app)
    session = test_studio.save_capture(
        b"fake-webm-data",
        "review.webm",
        "Long after reclaim.",
        mic_enabled=True,
    )
    test_memory = TradingMemory(tmp_path)
    review = test_memory.save_review(session, {"summary": "Saved review.", "setup_type": "Range reclaim"})
    monkeypatch.setattr("app.backend.trading_memory", test_memory)
    test_studio.record_review(session.id, review)

    response = client.post(
        f"/api/captures/{session.id}/export",
        json={"name": "Missing key", "export_type": "pine", "export_mode": "ai"},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Gemini API key missing."


def test_capture_ai_review_disabled_fails_cleanly(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("ASTRA_AI_BRAIN_ENABLED", "true")
    monkeypatch.setenv("ASTRA_AI_REVIEWS_ENABLED", "false")
    monkeypatch.setenv("GEMINI_API_KEY", "fake-key")
    test_studio = CaptureStudio(tmp_path)
    test_generator = PineStrategyGenerator(tmp_path)
    test_memory = TradingMemory(tmp_path)
    monkeypatch.setattr("app.backend.capture_studio", test_studio)
    monkeypatch.setattr("app.backend.trading_memory", test_memory)
    monkeypatch.setattr("app.backend.ai_brain", MultimodalAIBrain(tmp_path, test_generator))
    client = TestClient(app)
    session = test_studio.save_capture(b"fake-webm-data", "review.webm", "Long after reclaim.", mic_enabled=True)

    response = client.post(f"/api/captures/{session.id}/review")

    assert response.status_code == 400
    assert response.json()["detail"] == "AI reviews disabled."


def test_capture_ai_review_missing_key_fails_cleanly(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("ASTRA_AI_BRAIN_ENABLED", "true")
    monkeypatch.setenv("ASTRA_AI_REVIEWS_ENABLED", "true")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    test_studio = CaptureStudio(tmp_path)
    test_generator = PineStrategyGenerator(tmp_path)
    test_memory = TradingMemory(tmp_path)
    monkeypatch.setattr("app.backend.capture_studio", test_studio)
    monkeypatch.setattr("app.backend.trading_memory", test_memory)
    monkeypatch.setattr("app.backend.ai_brain", MultimodalAIBrain(tmp_path, test_generator))
    client = TestClient(app)
    session = test_studio.save_capture(b"fake-webm-data", "review.webm", "Long after reclaim.", mic_enabled=True)

    response = client.post(f"/api/captures/{session.id}/review")

    assert response.status_code == 400
    assert response.json()["detail"] == "Gemini API key missing."


def test_capture_ai_review_saves_metadata_and_memory(tmp_path: Path, monkeypatch):
    class FakeGeminiClient:
        model = "gemini-review-test"

        @property
        def configured(self) -> bool:
            return True

        def generate_from_video(self, video_path: Path, prompt: str) -> str:
            assert video_path.name.endswith(".webm")
            assert "direct trading coach" in prompt
            return (
                '{"summary":"Direct coach summary.","trade_grade":"B","setup_type":"Range reclaim",'
                '"strengths":["Clear context"],"mistakes":["Late entry"],'
                '"timestamped_notes":[{"timecode":"00:45","label":"Late entry",'
                '"observation":"Entry came after expansion.","coaching_note":"Take it closer to reclaim.",'
                '"severity":"high"}],"strategy_rules":["Skip late expansion"],'
                '"next_practice_focus":"Wait for cleaner entry location.",'
                '"voice_summary":"Good context, late execution."}'
            )

    monkeypatch.setenv("ASTRA_AI_BRAIN_ENABLED", "true")
    monkeypatch.setenv("ASTRA_AI_REVIEWS_ENABLED", "true")
    monkeypatch.setenv("ASTRA_AI_BRAIN_PROVIDER", "gemini")
    monkeypatch.setenv("GEMINI_API_KEY", "fake-key")
    test_studio = CaptureStudio(tmp_path)
    test_generator = PineStrategyGenerator(tmp_path)
    test_memory = TradingMemory(tmp_path)
    monkeypatch.setattr("app.backend.capture_studio", test_studio)
    monkeypatch.setattr("app.backend.trading_memory", test_memory)
    monkeypatch.setattr("app.backend.ai_brain", MultimodalAIBrain(tmp_path, test_generator, client=FakeGeminiClient()))
    client = TestClient(app)
    session = test_studio.save_capture(b"fake-webm-data", "review.webm", "I entered after the reclaim.", mic_enabled=True)

    response = client.post(f"/api/captures/{session.id}/review")
    payload = response.json()

    assert response.status_code == 200
    assert payload["review"]["source"] == "ai_multimodal_review"
    assert payload["capture"]["ai_review_status"] == "complete"
    assert payload["capture"]["setup_type"] == "Range reclaim"
    assert payload["capture"]["trade_grade"] == "B"
    assert payload["capture"]["mistake_markers"][0]["label"] == "Late entry"
    assert payload["memory"]["total_reviews"] == 1
    assert test_memory.get_review(test_studio.get_capture(session.id))["summary"] == "Direct coach summary."

    fetched = client.get(f"/api/captures/{session.id}/review")
    memory_response = client.get("/api/trading-memory/summary")

    assert fetched.status_code == 200
    assert fetched.json()["review"]["trade_grade"] == "B"
    assert memory_response.status_code == 200
    assert memory_response.json()["summary"]["common_setups"][0]["setup_type"] == "Range reclaim"


def test_capture_ai_review_rejects_missing_video(tmp_path: Path, monkeypatch):
    class FakeGeminiClient:
        model = "gemini-review-test"

        @property
        def configured(self) -> bool:
            return True

        def generate_from_video(self, video_path: Path, prompt: str) -> str:
            raise AssertionError("Review should not call the model without video.")

    monkeypatch.setenv("ASTRA_AI_BRAIN_ENABLED", "true")
    monkeypatch.setenv("ASTRA_AI_REVIEWS_ENABLED", "true")
    monkeypatch.setenv("GEMINI_API_KEY", "fake-key")
    test_studio = CaptureStudio(tmp_path)
    test_memory = TradingMemory(tmp_path)
    monkeypatch.setattr("app.backend.capture_studio", test_studio)
    monkeypatch.setattr("app.backend.trading_memory", test_memory)
    monkeypatch.setattr("app.backend.ai_brain", MultimodalAIBrain(tmp_path, PineStrategyGenerator(tmp_path), client=FakeGeminiClient()))
    client = TestClient(app)
    session = test_studio.save_capture(b"fake-webm-data", "missing.webm", "Transcript exists.", mic_enabled=True)
    Path(session.path).unlink()

    response = client.post(f"/api/captures/{session.id}/review")

    assert response.status_code == 400
    assert "video file is missing" in response.json()["detail"].lower()


def test_capture_ai_review_rejects_video_without_audio_or_transcript(tmp_path: Path, monkeypatch):
    class FakeGeminiClient:
        model = "gemini-review-test"

        @property
        def configured(self) -> bool:
            return True

        def generate_from_video(self, video_path: Path, prompt: str) -> str:
            raise AssertionError("Review should require audio or transcript context.")

    monkeypatch.setenv("ASTRA_AI_BRAIN_ENABLED", "true")
    monkeypatch.setenv("ASTRA_AI_REVIEWS_ENABLED", "true")
    monkeypatch.setenv("GEMINI_API_KEY", "fake-key")
    test_studio = CaptureStudio(tmp_path)
    test_memory = TradingMemory(tmp_path)
    monkeypatch.setattr("app.backend.capture_studio", test_studio)
    monkeypatch.setattr("app.backend.trading_memory", test_memory)
    monkeypatch.setattr("app.backend.ai_brain", MultimodalAIBrain(tmp_path, PineStrategyGenerator(tmp_path), client=FakeGeminiClient()))
    client = TestClient(app)
    session = test_studio.save_capture(b"fake-webm-data", "silent.webm")

    response = client.post(f"/api/captures/{session.id}/review")

    assert response.status_code == 400
    assert "mic audio or a transcript" in response.json()["detail"]


def test_capture_ai_export_uses_saved_review_and_records_source(tmp_path: Path, monkeypatch):
    class FakeVideoClient:
        model = "gemini-video-test"

        @property
        def configured(self) -> bool:
            return True

        def generate_from_video(self, video_path: Path, prompt: str) -> str:
            raise AssertionError("AI export should not upload video when saved review exists.")

    class FakeTextClient:
        model = "gemini-text-test"

        @property
        def configured(self) -> bool:
            return True

        def generate(self, prompt: str) -> str:
            assert "Selected transcript reclaiming high" in prompt
            assert "Saved AI review" in prompt
            assert "Wait for cleaner reclaim" in prompt
            assert "Trading memory summary" in prompt
            return (
                '{"title":"Selected AI Strategy","summary":"Selected capture AI export.",'
                '"exports":{"instructions":"<!doctype html><html><body>AI playbook</body></html>"}}'
            )

    monkeypatch.setenv("ASTRA_AI_BRAIN_ENABLED", "true")
    monkeypatch.setenv("ASTRA_AI_EXPORTS_ENABLED", "true")
    monkeypatch.setenv("ASTRA_AI_BRAIN_PROVIDER", "gemini")
    monkeypatch.setenv("GEMINI_API_KEY", "fake-key")
    test_studio = CaptureStudio(tmp_path)
    test_generator = PineStrategyGenerator(tmp_path)
    test_memory = TradingMemory(tmp_path)
    monkeypatch.setattr("app.backend.capture_studio", test_studio)
    monkeypatch.setattr("app.backend.trading_memory", test_memory)
    monkeypatch.setattr("app.backend.ai_brain", MultimodalAIBrain(tmp_path, test_generator, client=FakeVideoClient(), text_client=FakeTextClient()))
    client = TestClient(app)
    session = test_studio.save_capture(
        b"fake-webm-data",
        "selected.webm",
        "Selected transcript reclaiming high.",
        mic_enabled=True,
    )
    saved_review = test_memory.save_review(
        session,
        {
            "summary": "Wait for cleaner reclaim.",
            "trade_grade": "B",
            "setup_type": "Range reclaim",
            "strategy_rules": ["Wait for cleaner reclaim"],
        },
    )
    test_studio.record_review(session.id, saved_review)

    response = client.post(
        f"/api/captures/{session.id}/export",
        json={"name": "Selected AI Strategy", "export_type": "instructions", "export_mode": "ai"},
    )
    payload = response.json()

    assert response.status_code == 200
    assert payload["strategy"]["source"] == "ai_review_memory"
    assert payload["strategy"]["model"] == "gemini-text-test"
    assert payload["strategy"]["download_url"].endswith(".html")
    assert payload["capture"]["generated_exports"][-1]["source"] == "ai_review_memory"


def test_capture_ai_export_requires_saved_review_before_export(tmp_path: Path, monkeypatch):
    class FakeTextClient:
        model = "gemini-text-test"

        @property
        def configured(self) -> bool:
            return True

        def generate(self, prompt: str) -> str:
            raise AssertionError("AI export should not run before review exists.")

    monkeypatch.setenv("ASTRA_AI_BRAIN_ENABLED", "true")
    monkeypatch.setenv("ASTRA_AI_EXPORTS_ENABLED", "true")
    monkeypatch.setenv("ASTRA_AI_BRAIN_PROVIDER", "gemini")
    monkeypatch.setenv("GEMINI_API_KEY", "fake-key")
    test_studio = CaptureStudio(tmp_path)
    test_generator = PineStrategyGenerator(tmp_path)
    monkeypatch.setattr("app.backend.capture_studio", test_studio)
    monkeypatch.setattr("app.backend.trading_memory", TradingMemory(tmp_path))
    monkeypatch.setattr("app.backend.ai_brain", MultimodalAIBrain(tmp_path, test_generator, text_client=FakeTextClient()))
    client = TestClient(app)
    session = test_studio.save_capture(b"fake-webm-data", "review-needed.webm", "Transcript exists.", mic_enabled=True)

    response = client.post(
        f"/api/captures/{session.id}/export",
        json={"name": "Needs review", "export_type": "pine", "export_mode": "ai"},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Run AI Review before AI export."


def test_capture_ai_export_can_use_saved_review_even_if_video_is_gone(tmp_path: Path, monkeypatch):
    class FakeTextClient:
        model = "gemini-text-test"

        @property
        def configured(self) -> bool:
            return True

        def generate(self, prompt: str) -> str:
            assert "Saved AI review" in prompt
            return (
                '{"title":"Reviewed Strategy","summary":"Generated from saved review.",'
                '"exports":{"pine":"//@version=6\\nstrategy(\\"Reviewed\\", overlay=true)"}}'
            )

    monkeypatch.setenv("ASTRA_AI_BRAIN_ENABLED", "true")
    monkeypatch.setenv("ASTRA_AI_EXPORTS_ENABLED", "true")
    monkeypatch.setenv("ASTRA_AI_BRAIN_PROVIDER", "gemini")
    monkeypatch.setenv("GEMINI_API_KEY", "fake-key")
    test_studio = CaptureStudio(tmp_path)
    test_generator = PineStrategyGenerator(tmp_path)
    test_memory = TradingMemory(tmp_path)
    monkeypatch.setattr("app.backend.capture_studio", test_studio)
    monkeypatch.setattr("app.backend.trading_memory", test_memory)
    monkeypatch.setattr("app.backend.ai_brain", MultimodalAIBrain(tmp_path, test_generator, text_client=FakeTextClient()))
    client = TestClient(app)
    session = test_studio.save_capture(b"fake-webm-data", "missing-after-review.webm", "Transcript exists.", mic_enabled=True)
    review = test_memory.save_review(session, {"summary": "Saved AI review.", "setup_type": "Range reclaim"})
    test_studio.record_review(session.id, review)
    Path(session.path).unlink()

    response = client.post(
        f"/api/captures/{session.id}/export",
        json={"name": "Reviewed Strategy", "export_type": "pine", "export_mode": "ai"},
    )

    assert response.status_code == 200
    assert response.json()["strategy"]["source"] == "ai_review_memory"


def test_capture_export_fails_without_transcript(tmp_path: Path, monkeypatch):
    test_studio = CaptureStudio(tmp_path)
    monkeypatch.setattr("app.backend.capture_studio", test_studio)
    client = TestClient(app)
    session = test_studio.save_capture(b"fake-webm-data", "silent.webm")

    response = client.post(
        f"/api/captures/{session.id}/export",
        json={"name": "Silent capture", "export_type": "pine", "export_mode": "local"},
    )

    assert response.status_code == 400
    assert "no transcript" in response.json()["detail"].lower()


def test_old_dashboard_static_files_are_removed():
    root = Path(__file__).resolve().parents[1]

    assert not (root / "web" / "index.html").exists()
    assert not (root / "web" / "app.js").exists()
    assert not (root / "web" / "styles.css").exists()
