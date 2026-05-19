from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date

from app.notifications import notification_channels
from app.skills_registry import trading_intel_skills


@dataclass(frozen=True)
class CommandCenterState:
    session_date: str
    title: str
    market_prep: dict
    watchlist: list[dict]
    trade_plans: list[dict]
    journal: list[dict]
    agent_tasks: list[dict]
    intel_tasks: list[dict]
    notification_channels: list[dict]
    workflow_notes: list[str]

    def to_dict(self) -> dict:
        return asdict(self)


def default_command_center_state() -> CommandCenterState:
    return CommandCenterState(
        session_date=date.today().isoformat(),
        title="AstraCore Trading Command Center",
        market_prep={
            "status": "not_started",
            "bias": "unset",
            "focus": ["NQ", "ES", "QQQ", "SPY", "BTC"],
            "news": "Live economic calendar is not wired yet.",
            "risk_mode": "define max daily loss before trading",
        },
        watchlist=[
            {"symbol": "NQ", "status": "tracking", "note": "Wire market data before analysis."},
            {"symbol": "ES", "status": "tracking", "note": "Use for broader index confirmation."},
            {"symbol": "QQQ", "status": "tracking", "note": "Equity proxy for Nasdaq context."},
            {"symbol": "BTC", "status": "optional", "note": "Crypto route later."},
        ],
        trade_plans=[],
        journal=[],
        agent_tasks=[
            {
                "owner": "Codex",
                "lane": "implementation",
                "task": "Build command center shell, tests, and local persistence.",
                "status": "active",
            },
            {
                "owner": "Claude Code",
                "lane": "strategy",
                "task": "Draft trading workflow specs, UX critique, and prompt/playbook notes.",
                "status": "waiting",
            },
        ],
        intel_tasks=[
            {
                "skill_id": skill.id,
                "title": skill.title,
                "cadence": skill.cadence,
                "status": skill.status,
                "tools_needed": skill.tools_needed,
            }
            for skill in trading_intel_skills()
        ],
        notification_channels=[channel.to_dict() for channel in notification_channels()],
        workflow_notes=[
            "Codex owns code changes, tests, commits, and local verification.",
            "Claude Code can be used as a separate worker for specs, critique, and alternate implementation notes.",
            "Do not let Codex and Claude edit the same files at the same time without file ownership.",
        ],
    )
