from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class DecisionOption:
    """An option for decision making."""
    option_id: str
    description: str
    pros: list[str]
    cons: list[str]
    risk_level: float  # 0.0 = low risk, 1.0 = high risk
    expected_impact: float  # 0.0 = low impact, 1.0 = high impact
    confidence: float  # 0.0 = low confidence, 1.0 = high confidence
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class Decision:
    """A decision record."""
    decision_id: str
    question: str
    options: list[DecisionOption]
    selected_option: Optional[DecisionOption]
    reasoning: str
    timestamp: float
    outcome: Optional[str] = None
    metadata: dict[str, Any] = field(default_factory=dict)


class DecisionFramework:
    """Risk assessment and cost-benefit analysis for decision making."""

    def __init__(self):
        self._decisions: dict[str, Decision] = {}
        self._decision_counter = 0

    def evaluate_options(
        self,
        question: str,
        options: list[dict[str, Any]],
    ) -> list[DecisionOption]:
        """Evaluate options for a decision."""
        evaluated_options = []

        for i, option_data in enumerate(options):
            option = DecisionOption(
                option_id=f"opt_{i + 1}",
                description=option_data.get("description", ""),
                pros=option_data.get("pros", []),
                cons=option_data.get("cons", []),
                risk_level=self._assess_risk(option_data),
                expected_impact=self._assess_impact(option_data),
                confidence=option_data.get("confidence", 0.5),
                metadata=option_data.get("metadata", {}),
            )
            evaluated_options.append(option)

        return evaluated_options

    def _assess_risk(self, option_data: dict[str, Any]) -> float:
        """Assess risk level of an option."""
        risk = 0.0

        # Check for high-risk keywords
        high_risk_keywords = [
            "exploit", "attack", "intrusion", "escalation",
            "lateral movement", "persistence", "exfiltration",
        ]
        description = option_data.get("description", "").lower()
        for keyword in high_risk_keywords:
            if keyword in description:
                risk += 0.2

        # Check cons for risk indicators
        cons = option_data.get("cons", [])
        for con in cons:
            if any(keyword in con.lower() for keyword in ["risk", "danger", "detection", "noise"]):
                risk += 0.1

        return min(1.0, risk)

    def _assess_impact(self, option_data: dict[str, Any]) -> float:
        """Assess expected impact of an option."""
        impact = 0.5  # Default medium impact

        # Check for high-impact keywords
        high_impact_keywords = [
            "critical", "high", "root", "admin", "domain",
            "full access", "compromise", "complete",
        ]
        description = option_data.get("description", "").lower()
        for keyword in high_impact_keywords:
            if keyword in description:
                impact += 0.1

        # Check pros for impact indicators
        pros = option_data.get("pros", [])
        for pro in pros:
            if any(keyword in pro.lower() for keyword in ["access", "privilege", "control", "data"]):
                impact += 0.05

        return min(1.0, impact)

    def make_decision(
        self,
        question: str,
        options: list[dict[str, Any]],
        context: Optional[dict[str, Any]] = None,
    ) -> Decision:
        """Make a decision based on evaluated options."""
        # Evaluate options
        evaluated_options = self.evaluate_options(question, options)

        # Select best option based on risk-adjusted impact
        best_option = None
        best_score = -1

        for option in evaluated_options:
            # Score = impact * (1 - risk) * confidence
            score = option.expected_impact * (1 - option.risk_level) * option.confidence
            if score > best_score:
                best_score = score
                best_option = option

        # Create decision record
        self._decision_counter += 1
        decision = Decision(
            decision_id=f"dec_{self._decision_counter}",
            question=question,
            options=evaluated_options,
            selected_option=best_option,
            reasoning=self._generate_reasoning(evaluated_options, best_option),
            timestamp=time.time(),
            metadata=context or {},
        )

        self._decisions[decision.decision_id] = decision
        logger.info(f"Decision made: {decision.decision_id}")
        return decision

    def _generate_reasoning(
        self,
        options: list[DecisionOption],
        selected: Optional[DecisionOption],
    ) -> str:
        """Generate reasoning for the decision."""
        if not selected:
            return "No suitable option found"

        reasoning = f"Selected option '{selected.description}' because: "
        reasons = []

        if selected.expected_impact > 0.7:
            reasons.append("high expected impact")
        if selected.risk_level < 0.3:
            reasons.append("low risk profile")
        if selected.confidence > 0.7:
            reasons.append("high confidence")

        if reasons:
            reasoning += ", ".join(reasons)
        else:
            reasoning += "best overall score among available options"

        return reasoning

    def record_outcome(
        self,
        decision_id: str,
        outcome: str,
    ) -> Optional[Decision]:
        """Record the outcome of a decision."""
        if decision_id not in self._decisions:
            return None

        decision = self._decisions[decision_id]
        decision.outcome = outcome
        logger.info(f"Decision outcome recorded: {decision_id} -> {outcome}")
        return decision

    def analyze_decisions(
        self,
        question_pattern: Optional[str] = None,
    ) -> dict[str, Any]:
        """Analyze past decisions for patterns."""
        decisions = list(self._decisions.values())

        if question_pattern:
            decisions = [
                d for d in decisions
                if question_pattern.lower() in d.question.lower()
            ]

        if not decisions:
            return {"total_decisions": 0}

        outcomes = [d.outcome for d in decisions if d.outcome]
        successful = sum(1 for o in outcomes if o == "success")

        return {
            "total_decisions": len(decisions),
            "outcomes_recorded": len(outcomes),
            "success_rate": successful / len(outcomes) if outcomes else 0,
            "avg_risk_level": (
                sum(
                    d.selected_option.risk_level
                    for d in decisions
                    if d.selected_option
                ) / len(decisions)
            ),
        }

    def get_statistics(self) -> dict[str, Any]:
        """Get decision framework statistics."""
        return {
            "total_decisions": len(self._decisions),
            "decisions_with_outcomes": sum(
                1 for d in self._decisions.values() if d.outcome
            ),
        }


# Global instance
_decision_framework: Optional[DecisionFramework] = None


def get_decision_framework() -> DecisionFramework:
    """Get the global decision framework instance."""
    global _decision_framework
    if _decision_framework is None:
        _decision_framework = DecisionFramework()
    return _decision_framework
