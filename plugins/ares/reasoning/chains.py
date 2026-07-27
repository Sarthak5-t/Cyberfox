from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class ReasoningStep:
    """A single step in a reasoning chain."""
    step_id: str
    description: str
    input_data: Any
    output_data: Any
    confidence: float
    duration: float
    timestamp: float
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ReasoningChain:
    """A chain of reasoning steps."""
    chain_id: str
    goal: str
    steps: list[ReasoningStep]
    final_conclusion: Any
    overall_confidence: float
    total_duration: float
    created_at: float
    metadata: dict[str, Any] = field(default_factory=dict)


class ReasoningChainBuilder:
    """Multi-step reasoning for vulnerability analysis and exploit development."""

    def __init__(self):
        self._chains: dict[str, ReasoningChain] = {}
        self._chain_counter = 0

    def start_chain(
        self,
        goal: str,
        metadata: Optional[dict[str, Any]] = None,
    ) -> str:
        """Start a new reasoning chain."""
        self._chain_counter += 1
        chain_id = f"chain_{self._chain_counter}"
        logger.info(f"Reasoning chain started: {chain_id}")
        return chain_id

    def add_step(
        self,
        chain_id: str,
        description: str,
        input_data: Any,
        output_data: Any,
        confidence: float,
        duration: float,
        metadata: Optional[dict[str, Any]] = None,
    ) -> ReasoningStep:
        """Add a step to a reasoning chain."""
        step = ReasoningStep(
            step_id=f"{chain_id}_step_{len(self._chains.get(chain_id, ReasoningChain(
                chain_id=chain_id,
                goal="",
                steps=[],
                final_conclusion=None,
                overall_confidence=0,
                total_duration=0,
                created_at=time.time(),
            )).steps) + 1}",
            description=description,
            input_data=input_data,
            output_data=output_data,
            confidence=confidence,
            duration=duration,
            timestamp=time.time(),
            metadata=metadata or {},
        )

        if chain_id not in self._chains:
            self._chains[chain_id] = ReasoningChain(
                chain_id=chain_id,
                goal="",
                steps=[],
                final_conclusion=None,
                overall_confidence=0,
                total_duration=0,
                created_at=time.time(),
            )

        self._chains[chain_id].steps.append(step)
        self._chains[chain_id].total_duration += duration

        logger.debug(f"Step added to chain {chain_id}: {description}")
        return step

    def complete_chain(
        self,
        chain_id: str,
        conclusion: Any,
    ) -> Optional[ReasoningChain]:
        """Complete a reasoning chain with a final conclusion."""
        if chain_id not in self._chains:
            return None

        chain = self._chains[chain_id]
        chain.final_conclusion = conclusion

        # Calculate overall confidence (average of step confidences)
        if chain.steps:
            chain.overall_confidence = (
                sum(s.confidence for s in chain.steps) / len(chain.steps)
            )

        logger.info(
            f"Chain {chain_id} completed with "
            f"{len(chain.steps)} steps, confidence: {chain.overall_confidence:.2f}"
        )
        return chain

    def get_chain(self, chain_id: str) -> Optional[ReasoningChain]:
        """Get a reasoning chain."""
        return self._chains.get(chain_id)

    def analyze_chain(self, chain_id: str) -> dict[str, Any]:
        """Analyze a reasoning chain for insights."""
        chain = self.get_chain(chain_id)
        if not chain:
            return {"error": "Chain not found"}

        analysis = {
            "chain_id": chain_id,
            "goal": chain.goal,
            "steps_count": len(chain.steps),
            "overall_confidence": chain.overall_confidence,
            "total_duration": chain.total_duration,
            "avg_step_duration": (
                chain.total_duration / len(chain.steps) if chain.steps else 0
            ),
            "confidence_trend": self._get_confidence_trend(chain),
            "bottlenecks": self._find_bottlenecks(chain),
        }

        return analysis

    def _get_confidence_trend(self, chain: ReasoningChain) -> list[float]:
        """Get confidence trend across steps."""
        return [step.confidence for step in chain.steps]

    def _find_bottlenecks(self, chain: ReasoningChain) -> list[dict[str, Any]]:
        """Find bottlenecks in the reasoning chain."""
        bottlenecks = []

        if not chain.steps:
            return bottlenecks

        # Find steps with low confidence
        for step in chain.steps:
            if step.confidence < 0.5:
                bottlenecks.append({
                    "step": step.step_id,
                    "issue": "low_confidence",
                    "confidence": step.confidence,
                })

        # Find steps with high duration
        avg_duration = chain.total_duration / len(chain.steps)
        for step in chain.steps:
            if step.duration > avg_duration * 2:
                bottlenecks.append({
                    "step": step.step_id,
                    "issue": "high_duration",
                    "duration": step.duration,
                })

        return bottlenecks

    def get_statistics(self) -> dict[str, Any]:
        """Get reasoning chain statistics."""
        if not self._chains:
            return {"total_chains": 0}

        chains = list(self._chains.values())
        total_steps = sum(len(c.steps) for c in chains)

        return {
            "total_chains": len(chains),
            "total_steps": total_steps,
            "avg_steps_per_chain": total_steps / len(chains),
            "avg_confidence": (
                sum(c.overall_confidence for c in chains) / len(chains)
            ),
            "avg_duration": (
                sum(c.total_duration for c in chains) / len(chains)
            ),
        }


# Global instance
_reasoning_chains: Optional[ReasoningChainBuilder] = None


def get_reasoning_chains() -> ReasoningChainBuilder:
    """Get the global reasoning chain builder instance."""
    global _reasoning_chains
    if _reasoning_chains is None:
        _reasoning_chains = ReasoningChainBuilder()
    return _reasoning_chains
