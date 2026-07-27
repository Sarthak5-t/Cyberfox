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
class LearningExperience:
    """A learning experience from skill execution."""
    experience_id: str
    skill_id: str
    agent_id: str
    engagement_id: int
    timestamp: float
    input_params: dict[str, Any]
    output: Any
    outcome: str
    duration: float
    context: dict[str, Any] = field(default_factory=dict)
    lessons_learned: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class OptimizationRule:
    """A rule for optimizing skill execution."""
    rule_id: str
    skill_id: str
    condition: str
    action: str
    confidence: float
    usage_count: int = 0
    last_used: Optional[float] = None
    created_at: float = field(default_factory=time.time)


class SkillLearner:
    """Learns from past executions to optimize skill parameters."""

    def __init__(self, storage_dir: Optional[Path] = None):
        self._experiences: dict[str, list[LearningExperience]] = {}
        self._rules: dict[str, list[OptimizationRule]] = {}
        self._lock = threading.RLock()
        self._storage_dir = storage_dir or Path.home() / ".cyberfox" / "ares" / "skill_learning"
        self._storage_dir.mkdir(parents=True, exist_ok=True)
        self._experience_counter = 0

    def record_experience(
        self,
        skill_id: str,
        agent_id: str,
        engagement_id: int,
        input_params: dict[str, Any],
        output: Any,
        outcome: str,
        duration: float,
        context: Optional[dict[str, Any]] = None,
        lessons_learned: Optional[list[str]] = None,
    ) -> LearningExperience:
        """Record a learning experience."""
        with self._lock:
            self._experience_counter += 1
            experience = LearningExperience(
                experience_id=f"exp_{self._experience_counter}",
                skill_id=skill_id,
                agent_id=agent_id,
                engagement_id=engagement_id,
                timestamp=time.time(),
                input_params=input_params,
                output=output,
                outcome=outcome,
                duration=duration,
                context=context or {},
                lessons_learned=lessons_learned or [],
            )

            if skill_id not in self._experiences:
                self._experiences[skill_id] = []
            self._experiences[skill_id].append(experience)

            # Persist to disk
            self._persist_experience(experience)

            # Learn from experience
            self._learn_from_experience(experience)

            logger.info(f"Learning experience recorded: {experience.experience_id}")
            return experience

    def get_experiences(
        self,
        skill_id: str,
        outcome: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> list[LearningExperience]:
        """Get experiences for a skill."""
        with self._lock:
            if skill_id not in self._experiences:
                return []

            experiences = self._experiences[skill_id]

            if outcome:
                experiences = [e for e in experiences if e.outcome == outcome]

            if limit:
                experiences = experiences[-limit:]

            return experiences

    def get_successful_experiences(
        self,
        skill_id: str,
        limit: Optional[int] = None,
    ) -> list[LearningExperience]:
        """Get successful experiences for a skill."""
        return self.get_experiences(skill_id, outcome="success", limit=limit)

    def get_failed_experiences(
        self,
        skill_id: str,
        limit: Optional[int] = None,
    ) -> list[LearningExperience]:
        """Get failed experiences for a skill."""
        return self.get_experiences(skill_id, outcome="failure", limit=limit)

    def analyze_patterns(
        self,
        skill_id: str,
    ) -> dict[str, Any]:
        """Analyze patterns in skill experiences."""
        experiences = self.get_experiences(skill_id)
        if not experiences:
            return {}

        successful = [e for e in experiences if e.outcome == "success"]
        failed = [e for e in experiences if e.outcome == "failure"]

        patterns = {
            "total_experiences": len(experiences),
            "success_rate": len(successful) / len(experiences) if experiences else 0,
            "avg_duration": sum(e.duration for e in experiences) / len(experiences),
            "common_input_patterns": self._analyze_input_patterns(experiences),
            "common_failure_reasons": self._analyze_failures(failed),
            "optimal_parameters": self._find_optimal_parameters(successful),
        }

        return patterns

    def _analyze_input_patterns(
        self,
        experiences: list[LearningExperience],
    ) -> dict[str, Any]:
        """Analyze common input patterns."""
        patterns: dict[str, Any] = {}
        for exp in experiences:
            for key, value in exp.input_params.items():
                if key not in patterns:
                    patterns[key] = {"count": 0, "values": {}}
                patterns[key]["count"] += 1
                value_str = str(value)
                patterns[key]["values"][value_str] = (
                    patterns[key]["values"].get(value_str, 0) + 1
                )
        return patterns

    def _analyze_failures(
        self,
        failed_experiences: list[LearningExperience],
    ) -> list[dict[str, Any]]:
        """Analyze common failure reasons."""
        failure_reasons: dict[str, int] = {}
        for exp in failed_experiences:
            if exp.output and isinstance(exp.output, dict):
                error = exp.output.get("error", "unknown")
                failure_reasons[error] = failure_reasons.get(error, 0) + 1

        return [
            {"reason": reason, "count": count}
            for reason, count in sorted(
                failure_reasons.items(),
                key=lambda x: x[1],
                reverse=True,
            )
        ]

    def _find_optimal_parameters(
        self,
        successful_experiences: list[LearningExperience],
    ) -> dict[str, Any]:
        """Find optimal parameters from successful experiences."""
        if not successful_experiences:
            return {}

        # Find most common parameters in successful experiences
        param_counts: dict[str, dict[str, int]] = {}
        for exp in successful_experiences:
            for key, value in exp.input_params.items():
                if key not in param_counts:
                    param_counts[key] = {}
                value_str = str(value)
                param_counts[key][value_str] = (
                    param_counts[key].get(value_str, 0) + 1
                )

        # Return most common values
        optimal = {}
        for key, values in param_counts.items():
            optimal[key] = max(values.items(), key=lambda x: x[1])[0]

        return optimal

    def _learn_from_experience(self, experience: LearningExperience) -> None:
        """Learn from a single experience and create optimization rules."""
        # This is a simplified learning algorithm
        # In a real implementation, this could use more sophisticated ML

        if experience.outcome == "failure":
            # Create a rule to avoid this failure
            self._create_optimization_rule(
                skill_id=experience.skill_id,
                condition=f"input matches {experience.input_params}",
                action="review and adjust parameters",
                confidence=0.5,
            )
        elif experience.outcome == "success":
            # Create a rule to reinforce this success
            self._create_optimization_rule(
                skill_id=experience.skill_id,
                condition=f"input matches {experience.input_params}",
                action="use similar parameters",
                confidence=0.7,
            )

    def _create_optimization_rule(
        self,
        skill_id: str,
        condition: str,
        action: str,
        confidence: float,
    ) -> OptimizationRule:
        """Create or update an optimization rule."""
        with self._lock:
            if skill_id not in self._rules:
                self._rules[skill_id] = []

            # Check if similar rule exists
            for rule in self._rules[skill_id]:
                if rule.condition == condition:
                    rule.usage_count += 1
                    rule.last_used = time.time()
                    # Update confidence with exponential moving average
                    rule.confidence = (rule.confidence * 0.8) + (confidence * 0.2)
                    return rule

            # Create new rule
            rule_id = f"rule_{skill_id}_{len(self._rules[skill_id])}"
            rule = OptimizationRule(
                rule_id=rule_id,
                skill_id=skill_id,
                condition=condition,
                action=action,
                confidence=confidence,
                usage_count=1,
                last_used=time.time(),
            )
            self._rules[skill_id].append(rule)

            return rule

    def get_optimization_rules(
        self,
        skill_id: str,
        min_confidence: float = 0.5,
    ) -> list[OptimizationRule]:
        """Get optimization rules for a skill."""
        with self._lock:
            if skill_id not in self._rules:
                return []

            return [
                r for r in self._rules[skill_id]
                if r.confidence >= min_confidence
            ]

    def get_statistics(self) -> dict[str, Any]:
        """Get learning statistics."""
        with self._lock:
            stats = {
                "total_experiences": sum(
                    len(exps) for exps in self._experiences.values()
                ),
                "total_rules": sum(
                    len(rules) for rules in self._rules.values()
                ),
                "skills_learned": len(self._experiences),
                "avg_experiences_per_skill": 0,
            }

            if self._experiences:
                stats["avg_experiences_per_skill"] = (
                    stats["total_experiences"] / len(self._experiences)
                )

            return stats

    def _persist_experience(self, experience: LearningExperience) -> None:
        """Persist experience to disk."""
        try:
            skill_dir = self._storage_dir / experience.skill_id
            skill_dir.mkdir(exist_ok=True)

            exp_file = skill_dir / f"{experience.experience_id}.json"
            data = {
                "experience_id": experience.experience_id,
                "skill_id": experience.skill_id,
                "agent_id": experience.agent_id,
                "engagement_id": experience.engagement_id,
                "timestamp": experience.timestamp,
                "input_params": experience.input_params,
                "output": experience.output,
                "outcome": experience.outcome,
                "duration": experience.duration,
                "context": experience.context,
                "lessons_learned": experience.lessons_learned,
                "metadata": experience.metadata,
            }
            exp_file.write_text(json.dumps(data, indent=2))
            logger.debug(f"Experience persisted to {exp_file}")
        except Exception as e:
            logger.error(f"Failed to persist experience: {e}")


# Global instance
_skill_learner: Optional[SkillLearner] = None


def get_skill_learner() -> SkillLearner:
    """Get the global skill learner instance."""
    global _skill_learner
    if _skill_learner is None:
        _skill_learner = SkillLearner()
    return _skill_learner
