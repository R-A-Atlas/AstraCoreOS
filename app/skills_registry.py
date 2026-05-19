from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class IntelSkill:
    id: str
    title: str
    purpose: str
    cadence: str
    prompt_template: str
    tools_needed: list[str]
    status: str = "available"

    def to_dict(self) -> dict:
        return asdict(self)


def trading_intel_skills() -> list[IntelSkill]:
    return [
        IntelSkill(
            id="daily_market_prep",
            title="Daily Market Prep",
            purpose="Build the premarket brief: index context, key levels, calendar risk, and trade bias.",
            cadence="daily_before_open",
            prompt_template=(
                "Prepare today's trading brief. Include market structure, overnight range, "
                "economic calendar risk, key levels, invalidation points, and a no-trade condition."
            ),
            tools_needed=["market_data", "economic_calendar", "news_scan"],
        ),
        IntelSkill(
            id="nq_session_brief",
            title="NQ Session Brief",
            purpose="Summarize NQ-specific context for the current session without forcing a trade.",
            cadence="on_demand",
            prompt_template=(
                "Create an NQ session brief. Focus on trend, liquidity zones, volatility, "
                "session timing, and what would confirm or reject the setup."
            ),
            tools_needed=["futures_quote", "session_levels", "volatility_snapshot"],
        ),
        IntelSkill(
            id="risk_check",
            title="Risk Check",
            purpose="Audit the user's planned trade against max loss, position size, and emotional rules.",
            cadence="before_trade",
            prompt_template=(
                "Review this trade plan for risk. Check position size, max daily loss, stop logic, "
                "reward-to-risk, overtrading risk, and whether the plan is specific enough to execute."
            ),
            tools_needed=["account_rules", "position_sizer", "journal_memory"],
        ),
        IntelSkill(
            id="trade_plan_review",
            title="Trade Plan Review",
            purpose="Turn a raw idea into an executable plan with entry, invalidation, targets, and conditions.",
            cadence="on_demand",
            prompt_template=(
                "Convert this idea into a trade plan. Include thesis, entry trigger, stop, targets, "
                "time stop, invalidation, and reasons to skip."
            ),
            tools_needed=["market_data", "technical_context", "risk_check"],
        ),
        IntelSkill(
            id="journal_review",
            title="Journal Review",
            purpose="Analyze recent trade notes to find recurring behavior, mistakes, and improvement rules.",
            cadence="daily_after_close",
            prompt_template=(
                "Review today's journal. Extract patterns, mistakes, best execution moments, "
                "one rule to keep, one rule to change, and tomorrow's focus."
            ),
            tools_needed=["journal_memory", "trade_history"],
        ),
        IntelSkill(
            id="news_watch",
            title="News Watch",
            purpose="Watch public macro and market headlines for items that can change intraday risk.",
            cadence="every_30_minutes_when_enabled",
            prompt_template=(
                "Scan market news for risk events. Return only items that could change index, rates, "
                "dollar, or volatility conditions. Include source names and why each item matters."
            ),
            tools_needed=["web_search", "news_sources", "economic_calendar"],
            status="needs_web_tool",
        ),
        IntelSkill(
            id="agent_task_brief",
            title="Agent Task Brief",
            purpose="Generate clean task packets for Codex, Claude Code, or another worker agent.",
            cadence="on_demand",
            prompt_template=(
                "Turn this objective into a worker-ready brief. Include scope, files owned, acceptance "
                "tests, constraints, and what not to edit."
            ),
            tools_needed=["repo_context", "test_runner"],
        ),
    ]


def skill_catalog() -> dict:
    skills = [skill.to_dict() for skill in trading_intel_skills()]
    return {
        "domain": "trading_command_center",
        "count": len(skills),
        "skills": skills,
    }
