from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone

from app.agent_packets import ContextPacket
from app.skills_registry import IntelSkill, trading_intel_skills


@dataclass(frozen=True)
class IntelRunResult:
    ok: bool
    skill_id: str
    message: str
    packet: dict
    missing_tools: list[str]
    created_at: str

    def to_dict(self) -> dict:
        return asdict(self)


class IntelRunner:
    def __init__(self) -> None:
        self._skills = {skill.id: skill for skill in trading_intel_skills()}
        self._wired_tools = {"repo_context", "test_runner", "journal_memory", "account_rules"}

    def run(self, skill_id: str, directive: str = "") -> IntelRunResult:
        skill = self._skills.get(skill_id)
        if not skill:
            return IntelRunResult(
                ok=False,
                skill_id=skill_id,
                message=f"Unknown intel skill: {skill_id}",
                packet={},
                missing_tools=[],
                created_at=self._now(),
            )

        missing_tools = [tool for tool in skill.tools_needed if tool not in self._wired_tools]
        packet = self._packet_for_skill(skill, directive, missing_tools)
        return IntelRunResult(
            ok=True,
            skill_id=skill.id,
            message=self._message_for_skill(skill, missing_tools),
            packet=packet.to_dict(),
            missing_tools=missing_tools,
            created_at=self._now(),
        )

    def _packet_for_skill(self, skill: IntelSkill, directive: str, missing_tools: list[str]) -> ContextPacket:
        data = {
            "skill_id": skill.id,
            "title": skill.title,
            "cadence": skill.cadence,
            "prompt_template": skill.prompt_template,
            "user_directive": directive,
            "wired_tools": [tool for tool in skill.tools_needed if tool in self._wired_tools],
            "missing_tools": missing_tools,
            "next_actions": self._next_actions(skill, missing_tools),
            "automation_status": "ready_for_local_use" if not missing_tools else "waiting_on_tool_wiring",
        }
        warnings = []
        if missing_tools:
            warnings.append("This skill is prompt-ready, but some data tools are not wired yet.")
        return ContextPacket(
            agent="trading_intel_skill_runner",
            task=skill.id,
            status="needs_tools" if missing_tools else "ready",
            summary=f"Prepared {skill.title} run packet.",
            confidence=0.82 if not missing_tools else 0.62,
            data=data,
            sources=["local:trading_intel_skill_registry"],
            warnings=warnings,
        )

    @staticmethod
    def _message_for_skill(skill: IntelSkill, missing_tools: list[str]) -> str:
        if not missing_tools:
            return f"{skill.title} is ready to run with local tools."
        return f"{skill.title} is staged. Missing tools before live automation: {', '.join(missing_tools)}."

    @staticmethod
    def _next_actions(skill: IntelSkill, missing_tools: list[str]) -> list[str]:
        if not missing_tools:
            return [
                "Use the prompt template as the worker instruction.",
                "Save the result into command-center memory.",
                "Review output before using it in trading decisions.",
            ]
        actions = [f"Wire tool: {tool}" for tool in missing_tools]
        actions.append(f"Then run {skill.id} on its cadence: {skill.cadence}.")
        return actions

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()
