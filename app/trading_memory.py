from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any


class TradingMemory:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.memory_dir = root / "workspace" / "memory"
        self.reviews_path = self.memory_dir / "trading_reviews.jsonl"

    def review_path_for(self, session: Any) -> Path:
        capture_path = Path(getattr(session, "path", ""))
        if capture_path.name:
            return capture_path.with_suffix(".review.json")
        return self.memory_dir / f"{getattr(session, 'id', 'capture')}.review.json"

    def get_review(self, session: Any) -> dict[str, Any] | None:
        path = self.review_path_for(session)
        if not path.exists() or not path.is_file():
            return None
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return None
        return payload if isinstance(payload, dict) else None

    def save_review(self, session: Any, review: dict[str, Any]) -> dict[str, Any]:
        normalized = self._normalize_review(session, review)
        path = self.review_path_for(session)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(normalized, indent=2) + "\n", encoding="utf-8")
        self._upsert_review_record(normalized)
        return normalized

    def all_reviews(self) -> list[dict[str, Any]]:
        if not self.reviews_path.exists():
            return []
        rows: list[dict[str, Any]] = []
        with self.reviews_path.open("r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    payload = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if isinstance(payload, dict):
                    rows.append(payload)
        return rows

    def summary(self) -> dict[str, Any]:
        reviews = self.all_reviews()
        setup_counts: Counter[str] = Counter()
        mistake_counts: Counter[str] = Counter()
        rules_to_keep: Counter[str] = Counter()
        rules_to_avoid: Counter[str] = Counter()
        grade_by_setup: dict[str, list[float]] = defaultdict(list)

        for review in reviews:
            setup = str(review.get("setup_type") or "Unclassified").strip() or "Unclassified"
            setup_counts[setup] += 1
            grade_by_setup[setup].append(self._grade_score(str(review.get("trade_grade") or "")))
            for mistake in self._string_list(review.get("mistakes")):
                mistake_counts[mistake] += 1
            for rule in self._string_list(review.get("strategy_rules")):
                rules_to_keep[rule] += 1
            for note in review.get("timestamped_notes") or []:
                if isinstance(note, dict) and str(note.get("severity", "")).lower() in {"high", "critical"}:
                    text = str(note.get("coaching_note") or note.get("observation") or "").strip()
                    if text:
                        rules_to_avoid[text] += 1

        best_scoring = []
        for setup, scores in grade_by_setup.items():
            if not scores:
                continue
            best_scoring.append(
                {
                    "setup_type": setup,
                    "count": len(scores),
                    "average_score": round(sum(scores) / len(scores), 2),
                }
            )
        best_scoring.sort(key=lambda item: (item["average_score"], item["count"]), reverse=True)

        repeated = [
            {"mistake": mistake, "count": count}
            for mistake, count in mistake_counts.most_common()
            if count > 1
        ]
        if not repeated:
            repeated = [{"mistake": mistake, "count": count} for mistake, count in mistake_counts.most_common(5)]

        return {
            "total_reviews": len(reviews),
            "common_setups": [
                {"setup_type": setup, "count": count}
                for setup, count in setup_counts.most_common(5)
            ],
            "repeated_mistakes": repeated[:8],
            "best_scoring_setups": best_scoring[:5],
            "rules_to_keep": [
                {"rule": rule, "count": count}
                for rule, count in rules_to_keep.most_common(8)
            ],
            "rules_to_avoid": [
                {"rule": rule, "count": count}
                for rule, count in rules_to_avoid.most_common(8)
            ],
            "coach_summary": self._coach_summary(len(reviews), setup_counts, mistake_counts),
        }

    def _upsert_review_record(self, review: dict[str, Any]) -> None:
        self.memory_dir.mkdir(parents=True, exist_ok=True)
        rows = [row for row in self.all_reviews() if row.get("capture_id") != review.get("capture_id")]
        rows.append(review)
        with self.reviews_path.open("w", encoding="utf-8") as fh:
            for row in rows:
                fh.write(json.dumps(row) + "\n")

    @staticmethod
    def _normalize_review(session: Any, review: dict[str, Any]) -> dict[str, Any]:
        timestamped_notes = []
        for raw in review.get("timestamped_notes") or []:
            if not isinstance(raw, dict):
                continue
            timestamped_notes.append(
                {
                    "timecode": str(raw.get("timecode") or "00:00").strip()[:16],
                    "label": str(raw.get("label") or "Observation").strip()[:80],
                    "observation": str(raw.get("observation") or "").strip()[:600],
                    "coaching_note": str(raw.get("coaching_note") or "").strip()[:600],
                    "severity": str(raw.get("severity") or "medium").strip().lower()[:20],
                }
            )
        return {
            "capture_id": str(getattr(session, "id", review.get("capture_id", ""))),
            "source": str(review.get("source") or "ai_multimodal_review"),
            "model": str(review.get("model") or ""),
            "summary": str(review.get("summary") or "").strip()[:1000],
            "trade_grade": str(review.get("trade_grade") or "Ungraded").strip()[:32],
            "setup_type": str(review.get("setup_type") or "Unclassified").strip()[:80],
            "strengths": TradingMemory._string_list(review.get("strengths"))[:8],
            "mistakes": TradingMemory._string_list(review.get("mistakes"))[:8],
            "timestamped_notes": timestamped_notes[:20],
            "strategy_rules": TradingMemory._string_list(review.get("strategy_rules"))[:12],
            "next_practice_focus": str(review.get("next_practice_focus") or "").strip()[:600],
            "voice_summary": str(review.get("voice_summary") or review.get("summary") or "").strip()[:600],
            "created_at": str(review.get("created_at") or datetime.now(timezone.utc).isoformat()),
        }

    @staticmethod
    def _string_list(value: Any) -> list[str]:
        if not isinstance(value, list):
            return []
        cleaned = []
        for item in value:
            text = str(item).strip()
            if text:
                cleaned.append(text[:240])
        return cleaned

    @staticmethod
    def _grade_score(grade: str) -> float:
        clean = grade.strip().upper()
        if clean.startswith("A"):
            return 4.0
        if clean.startswith("B"):
            return 3.0
        if clean.startswith("C"):
            return 2.0
        if clean.startswith("D"):
            return 1.0
        if clean.startswith("F"):
            return 0.0
        return 1.5

    @staticmethod
    def _coach_summary(total: int, setups: Counter[str], mistakes: Counter[str]) -> str:
        if total <= 0:
            return "No AI-reviewed trading sessions yet. Run an AI review from the Capture Library to start building memory."
        top_setup = setups.most_common(1)[0][0] if setups else "unclassified setups"
        top_mistake = mistakes.most_common(1)[0][0] if mistakes else "no repeated mistake tagged yet"
        return f"{total} reviewed session(s). Most common setup: {top_setup}. Main thing to watch: {top_mistake}."
