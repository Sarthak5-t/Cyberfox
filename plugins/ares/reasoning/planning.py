from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class PlanStep:
    """A step in a plan."""
    step_id: str
    description: str
    action: str
    parameters: dict[str, Any]
    dependencies: list[str]
    estimated_duration: float
    priority: int
    status: str = "pending"
    actual_duration: Optional[float] = None
    result: Any = None


@dataclass
class Plan:
    """A context-aware plan."""
    plan_id: str
    goal: str
    target: str
    steps: list[PlanStep]
    context: dict[str, Any]
    created_at: float
    updated_at: float
    status: str = "active"
    metadata: dict[str, Any] = field(default_factory=dict)


class ContextAwarePlanner:
    """Plan that considers target environment and discovered information."""

    def __init__(self):
        self._plans: dict[str, Plan] = {}
        self._plan_counter = 0

    def create_plan(
        self,
        goal: str,
        target: str,
        context: dict[str, Any],
        metadata: Optional[dict[str, Any]] = None,
    ) -> Plan:
        """Create a new context-aware plan."""
        self._plan_counter += 1
        plan_id = f"plan_{self._plan_counter}"

        # Generate steps based on goal and context
        steps = self._generate_steps(goal, target, context)

        plan = Plan(
            plan_id=plan_id,
            goal=goal,
            target=target,
            steps=steps,
            context=context,
            created_at=time.time(),
            updated_at=time.time(),
            metadata=metadata or {},
        )

        self._plans[plan_id] = plan
        logger.info(f"Plan created: {plan_id} with {len(steps)} steps")
        return plan

    def _generate_steps(
        self,
        goal: str,
        target: str,
        context: dict[str, Any],
    ) -> list[PlanStep]:
        """Generate plan steps based on goal and context."""
        steps = []
        step_counter = 0

        # Analyze context to determine appropriate steps
        services = context.get("services", [])
        vulnerabilities = context.get("vulnerabilities", [])
        known_info = context.get("known_info", {})

        # Basic recon step
        step_counter += 1
        steps.append(PlanStep(
            step_id=f"step_{step_counter}",
            description="Perform initial reconnaissance",
            action="recon",
            parameters={"target": target, "scan_type": "quick"},
            dependencies=[],
            estimated_duration=60.0,
            priority=1,
        ))

        # Service enumeration if services found
        if services:
            step_counter += 1
            steps.append(PlanStep(
                step_id=f"step_{step_counter}",
                description="Enumerate discovered services",
                action="enumerate",
                parameters={"target": target, "services": services},
                dependencies=[f"step_{step_counter - 1}"],
                estimated_duration=120.0,
                priority=2,
            ))

        # Vulnerability scanning
        step_counter += 1
        steps.append(PlanStep(
            step_id=f"step_{step_counter}",
            description="Scan for vulnerabilities",
            action="vuln_scan",
            parameters={"target": target, "services": services},
            dependencies=[f"step_{step_counter - 1}"],
            estimated_duration=180.0,
            priority=3,
        ))

        # Exploitation if vulnerabilities found
        if vulnerabilities:
            step_counter += 1
            steps.append(PlanStep(
                step_id=f"step_{step_counter}",
                description="Attempt exploitation of vulnerabilities",
                action="exploit",
                parameters={"target": target, "vulnerabilities": vulnerabilities},
                dependencies=[f"step_{step_counter - 1}"],
                estimated_duration=300.0,
                priority=4,
            ))

        # Post-exploitation
        step_counter += 1
        steps.append(PlanStep(
            step_id=f"step_{step_counter}",
            description="Post-exploitation activities",
            action="post_exploit",
            parameters={"target": target},
            dependencies=[f"step_{step_counter - 1}"],
            estimated_duration=240.0,
            priority=5,
        ))

        return steps

    def update_plan(
        self,
        plan_id: str,
        new_context: dict[str, Any],
    ) -> Optional[Plan]:
        """Update a plan based on new information."""
        if plan_id not in self._plans:
            return None

        plan = self._plans[plan_id]
        plan.context.update(new_context)
        plan.updated_at = time.time()

        # Regenerate steps with updated context
        plan.steps = self._generate_steps(
            plan.goal,
            plan.target,
            plan.context,
        )

        logger.info(f"Plan {plan_id} updated with new context")
        return plan

    def execute_step(
        self,
        plan_id: str,
        step_id: str,
        result: Any,
        duration: float,
    ) -> Optional[PlanStep]:
        """Mark a step as completed."""
        if plan_id not in self._plans:
            return None

        plan = self._plans[plan_id]
        for step in plan.steps:
            if step.step_id == step_id:
                step.status = "completed"
                step.result = result
                step.actual_duration = duration
                plan.updated_at = time.time()
                return step

        return None

    def get_next_step(self, plan_id: str) -> Optional[PlanStep]:
        """Get the next step to execute."""
        if plan_id not in self._plans:
            return None

        plan = self._plans[plan_id]
        for step in plan.steps:
            if step.status == "pending":
                # Check if dependencies are met
                deps_met = all(
                    any(
                        s.step_id == dep and s.status == "completed"
                        for s in plan.steps
                    )
                    for dep in step.dependencies
                )
                if deps_met:
                    return step

        return None

    def get_plan_progress(self, plan_id: str) -> dict[str, Any]:
        """Get plan execution progress."""
        if plan_id not in self._plans:
            return {"error": "Plan not found"}

        plan = self._plans[plan_id]
        total_steps = len(plan.steps)
        completed_steps = sum(1 for s in plan.steps if s.status == "completed")

        return {
            "plan_id": plan_id,
            "total_steps": total_steps,
            "completed_steps": completed_steps,
            "progress": completed_steps / total_steps if total_steps > 0 else 0,
            "status": plan.status,
        }

    def get_statistics(self) -> dict[str, Any]:
        """Get planning statistics."""
        if not self._plans:
            return {"total_plans": 0}

        plans = list(self._plans.values())
        total_steps = sum(len(p.steps) for p in plans)

        return {
            "total_plans": len(plans),
            "total_steps": total_steps,
            "avg_steps_per_plan": total_steps / len(plans),
        }


# Global instance
_context_planner: Optional[ContextAwarePlanner] = None


def get_context_planner() -> ContextAwarePlanner:
    """Get the global context-aware planner instance."""
    global _context_planner
    if _context_planner is None:
        _context_planner = ContextAwarePlanner()
    return _context_planner
