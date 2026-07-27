from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger(__name__)


class TaskComplexity:
    """Assess task complexity for adaptive thinking."""

    @staticmethod
    def assess(
        goal: str,
        context: str,
        target: str,
        available_info: dict[str, Any],
    ) -> float:
        """Assess complexity of a task (0.0 = simple, 1.0 = very complex)."""
        complexity = 0.0

        # Goal complexity
        goal_words = len(goal.split())
        if goal_words > 20:
            complexity += 0.2
        elif goal_words > 10:
            complexity += 0.1

        # Context complexity
        context_words = len(context.split())
        if context_words > 50:
            complexity += 0.2
        elif context_words > 20:
            complexity += 0.1

        # Target complexity
        if "," in target or "-" in target:  # Multiple targets
            complexity += 0.15

        # Available information
        if available_info:
            if len(available_info) > 10:
                complexity += 0.15
            elif len(available_info) > 5:
                complexity += 0.1

        # Keywords indicating complexity
        complex_keywords = [
            "chain", "multi-step", "advanced", "complex", "bypass",
            "evasion", "zero-day", "custom", "exploit development",
        ]
        for keyword in complex_keywords:
            if keyword in goal.lower() or keyword in context.lower():
                complexity += 0.1
                break

        return min(1.0, complexity)


@dataclass
class ThinkingBudget:
    """Computational budget for thinking."""
    max_iterations: int
    max_time_seconds: float
    confidence_threshold: float
    reasoning_depth: str  # "shallow", "medium", "deep"


class AdaptiveThinkingEngine:
    """Dynamic resource allocation based on task complexity."""

    def __init__(self):
        self._thinking_budgets: dict[str, ThinkingBudget] = {
            "shallow": ThinkingBudget(
                max_iterations=5,
                max_time_seconds=30.0,
                confidence_threshold=0.7,
                reasoning_depth="shallow",
            ),
            "medium": ThinkingBudget(
                max_iterations=15,
                max_time_seconds=120.0,
                confidence_threshold=0.8,
                reasoning_depth="medium",
            ),
            "deep": ThinkingBudget(
                max_iterations=50,
                max_time_seconds=300.0,
                confidence_threshold=0.9,
                reasoning_depth="deep",
            ),
        }
        self._execution_history: list[dict[str, Any]] = []

    def get_thinking_budget(
        self,
        goal: str,
        context: str,
        target: str,
        available_info: Optional[dict[str, Any]] = None,
    ) -> ThinkingBudget:
        """Get appropriate thinking budget for a task."""
        complexity = TaskComplexity.assess(
            goal=goal,
            context=context,
            target=target,
            available_info=available_info or {},
        )

        if complexity < 0.3:
            budget = self._thinking_budgets["shallow"]
        elif complexity < 0.7:
            budget = self._thinking_budgets["medium"]
        else:
            budget = self._thinking_budgets["deep"]

        logger.info(
            f"Task complexity: {complexity:.2f}, "
            f"Thinking budget: {budget.reasoning_depth}"
        )

        return budget

    def adapt_thinking(
        self,
        current_iteration: int,
        elapsed_time: float,
        current_confidence: float,
        budget: ThinkingBudget,
    ) -> dict[str, Any]:
        """Adapt thinking strategy based on progress."""
        time_ratio = elapsed_time / budget.max_time_seconds
        iteration_ratio = current_iteration / budget.max_iterations

        # Determine if we should continue, speed up, or stop
        if current_confidence >= budget.confidence_threshold:
            action = "stop"
            reason = f"Confidence {current_confidence:.2f} >= threshold {budget.confidence_threshold}"
        elif time_ratio > 0.8 and current_confidence < 0.5:
            action = "stop"
            reason = f"Time exhausted ({time_ratio:.0%}) with low confidence"
        elif iteration_ratio > 0.5 and current_confidence < 0.3:
            action = "change_strategy"
            reason = "Low confidence mid-way, try different approach"
        else:
            action = "continue"
            reason = "Progressing normally"

        return {
            "action": action,
            "reason": reason,
            "time_remaining": max(0, budget.max_time_seconds - elapsed_time),
            "iterations_remaining": max(0, budget.max_iterations - current_iteration),
            "confidence": current_confidence,
        }

    def record_execution(
        self,
        goal: str,
        complexity: float,
        budget: str,
        iterations: int,
        duration: float,
        final_confidence: float,
        outcome: str,
    ) -> None:
        """Record execution for future learning."""
        record = {
            "goal": goal,
            "complexity": complexity,
            "budget": budget,
            "iterations": iterations,
            "duration": duration,
            "final_confidence": final_confidence,
            "outcome": outcome,
            "timestamp": time.time(),
        }
        self._execution_history.append(record)

        # Keep only last 1000 records
        if len(self._execution_history) > 1000:
            self._execution_history = self._execution_history[-1000:]

    def get_statistics(self) -> dict[str, Any]:
        """Get adaptive thinking statistics."""
        if not self._execution_history:
            return {"total_executions": 0}

        complexities = [r["complexity"] for r in self._execution_history]
        durations = [r["duration"] for r in self._execution_history]
        confidences = [r["final_confidence"] for r in self._execution_history]

        return {
            "total_executions": len(self._execution_history),
            "avg_complexity": sum(complexities) / len(complexities),
            "avg_duration": sum(durations) / len(durations),
            "avg_confidence": sum(confidences) / len(confidences),
            "success_rate": sum(
                1 for r in self._execution_history if r["outcome"] == "success"
            ) / len(self._execution_history),
        }


# Global instance
_adaptive_engine: Optional[AdaptiveThinkingEngine] = None


def get_adaptive_engine() -> AdaptiveThinkingEngine:
    """Get the global adaptive thinking engine instance."""
    global _adaptive_engine
    if _adaptive_engine is None:
        _adaptive_engine = AdaptiveThinkingEngine()
    return _adaptive_engine
