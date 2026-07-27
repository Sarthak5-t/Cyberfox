from __future__ import annotations

import json
import logging
import time
import threading
from dataclasses import dataclass, field
from typing import Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class SkillScore:
    """Score for a skill."""
    skill_id: str
    success_rate: float
    efficiency_score: float
    reliability_score: float
    overall_score: float
    usage_count: int
    avg_duration: float
    last_calculated: float
    metadata: dict[str, Any] = field(default_factory=dict)


class SkillScorer:
    """Performance metrics and scoring for skills."""

    def __init__(self, storage_dir: Optional[Path] = None):
        self._scores: dict[str, SkillScore] = {}
        self._lock = threading.Lock()
        self._storage_dir = storage_dir or Path.home() / ".cyberfox" / "ares" / "skill_scores"
        self._storage_dir.mkdir(parents=True, exist_ok=True)

    def calculate_score(
        self,
        skill_id: str,
        success_rate: float,
        usage_count: int,
        avg_duration: float,
        target_duration: float = 60.0,  # Target duration in seconds
    ) -> SkillScore:
        """Calculate a comprehensive score for a skill."""
        # Efficiency score: how close to target duration
        if avg_duration > 0:
            efficiency = min(1.0, target_duration / avg_duration)
        else:
            efficiency = 1.0

        # Reliability score: based on usage count and success rate
        # More usage = higher reliability (up to a point)
        usage_factor = min(1.0, usage_count / 100)
        reliability = (success_rate * 0.7) + (usage_factor * 0.3)

        # Overall score: weighted combination
        overall = (success_rate * 0.4) + (efficiency * 0.3) + (reliability * 0.3)

        score = SkillScore(
            skill_id=skill_id,
            success_rate=success_rate,
            efficiency_score=efficiency,
            reliability_score=reliability,
            overall_score=overall,
            usage_count=usage_count,
            avg_duration=avg_duration,
            last_calculated=time.time(),
        )

        with self._lock:
            self._scores[skill_id] = score

        # Persist to disk
        self._persist_score(score)

        return score

    def get_score(self, skill_id: str) -> Optional[SkillScore]:
        """Get the score for a skill."""
        with self._lock:
            return self._scores.get(skill_id)

    def get_top_skills(
        self,
        category: Optional[str] = None,
        limit: int = 10,
    ) -> list[SkillScore]:
        """Get top skills by overall score."""
        with self._lock:
            scores = list(self._scores.values())
            scores.sort(key=lambda s: s.overall_score, reverse=True)
            return scores[:limit]

    def get_least_used_skills(self, limit: int = 10) -> list[SkillScore]:
        """Get least used skills."""
        with self._lock:
            scores = list(self._scores.values())
            scores.sort(key=lambda s: s.usage_count)
            return scores[:limit]

    def get_improvement_suggestions(self, skill_id: str) -> list[str]:
        """Get suggestions for improving a skill."""
        score = self.get_score(skill_id)
        if not score:
            return []

        suggestions = []

        if score.success_rate < 0.8:
            suggestions.append("Improve error handling and retry logic")

        if score.efficiency_score < 0.7:
            suggestions.append("Optimize execution flow to reduce duration")

        if score.reliability_score < 0.6:
            suggestions.append("Increase usage to build reliability confidence")

        if score.usage_count < 10:
            suggestions.append("Use this skill more frequently to gather metrics")

        return suggestions

    def compare_skills(
        self,
        skill_id_1: str,
        skill_id_2: str,
    ) -> dict[str, Any]:
        """Compare two skills."""
        score1 = self.get_score(skill_id_1)
        score2 = self.get_score(skill_id_2)

        if not score1 or not score2:
            return {"error": "One or both skills not found"}

        return {
            "skill_1": {
                "id": skill_id_1,
                "overall": score1.overall_score,
                "success_rate": score1.success_rate,
                "efficiency": score1.efficiency_score,
            },
            "skill_2": {
                "id": skill_id_2,
                "overall": score2.overall_score,
                "success_rate": score2.success_rate,
                "efficiency": score2.efficiency_score,
            },
            "winner": skill_id_1 if score1.overall_score > score2.overall_score else skill_id_2,
        }

    def get_statistics(self) -> dict[str, Any]:
        """Get scoring statistics."""
        with self._lock:
            if not self._scores:
                return {"total_skills": 0}

            scores = list(self._scores.values())
            return {
                "total_skills": len(scores),
                "avg_overall": sum(s.overall_score for s in scores) / len(scores),
                "avg_success_rate": sum(s.success_rate for s in scores) / len(scores),
                "avg_efficiency": sum(s.efficiency_score for s in scores) / len(scores),
                "avg_reliability": sum(s.reliability_score for s in scores) / len(scores),
            }

    def _persist_score(self, score: SkillScore) -> None:
        """Persist score to disk."""
        try:
            score_file = self._storage_dir / f"{score.skill_id}.json"
            data = {
                "skill_id": score.skill_id,
                "success_rate": score.success_rate,
                "efficiency_score": score.efficiency_score,
                "reliability_score": score.reliability_score,
                "overall_score": score.overall_score,
                "usage_count": score.usage_count,
                "avg_duration": score.avg_duration,
                "last_calculated": score.last_calculated,
                "metadata": score.metadata,
            }
            score_file.write_text(json.dumps(data, indent=2))
            logger.debug(f"Score persisted to {score_file}")
        except Exception as e:
            logger.error(f"Failed to persist score: {e}")


# Global instance
_skill_scorer: Optional[SkillScorer] = None


def get_skill_scorer() -> SkillScorer:
    """Get the global skill scorer instance."""
    global _skill_scorer
    if _skill_scorer is None:
        _skill_scorer = SkillScorer()
    return _skill_scorer
