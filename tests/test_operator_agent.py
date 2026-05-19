from pathlib import Path

from fastapi.testclient import TestClient

from app.backend import app
from app.capture_studio import CaptureStudio
from app.command_center import default_command_center_state
from app.config import AppConfig
from app.intel_runner import IntelRunner
from app.notifications import notification_channels
from app.operator_agent import OperatorAgent
from app.pine_generator import PineStrategyGenerator
from app.skills_registry import skill_catalog
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
    assert "reclaiming the prior candle high" in transcript_path.read_text(encoding="utf-8")
    assert "reclaiming the prior candle high" in studio.latest_transcript()


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
    assert instructions.filename.endswith(".md")
    assert "Execution Checklist" in instructions_content
    assert "reclaiming prior candle high" in instructions_content


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
    assert "Connect a display to begin" in response.text
    assert "/static/studio.js" in response.text


def test_root_route_serves_studio():
    client = TestClient(app)

    root_response = client.get("/")

    assert root_response.status_code == 200
    assert "AstraCore Studio" in root_response.text
    assert "/static/studio.js" in root_response.text
    assert "AstraCore Trading Command Center" not in root_response.text
    assert "/static/app.js" not in root_response.text
    assert root_response.headers["cache-control"] == "no-store"


def test_old_dashboard_static_files_are_removed():
    root = Path(__file__).resolve().parents[1]

    assert not (root / "web" / "index.html").exists()
    assert not (root / "web" / "app.js").exists()
    assert not (root / "web" / "styles.css").exists()
