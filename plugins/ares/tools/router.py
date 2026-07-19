from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

logger = logging.getLogger(__name__)


class ModelCapability(Enum):
    CHAT = "chat"
    CODE = "code"
    REASONING = "reasoning"
    TOOL_USE = "tool_use"
    FAST = "fast"
    CHEAP = "cheap"
    LOCAL = "local"


@dataclass
class RoutingRule:
    task_type: str
    preferred_capabilities: list[ModelCapability]
    max_cost_per_1k_tokens: float = 0.01
    max_latency_ms: int = 10000
    fallback_models: list[str] = field(default_factory=list)


@dataclass
class ModelProfile:
    model_id: str
    capabilities: list[ModelCapability]
    cost_per_1k_input: float
    cost_per_1k_output: float
    avg_latency_ms: int
    max_context: int
    supports_tools: bool


class ModelRouter:
    def __init__(self) -> None:
        self._profiles: dict[str, ModelProfile] = {}
        self._rules: dict[str, RoutingRule] = {}

    def register_model(self, profile: ModelProfile) -> None:
        self._profiles[profile.model_id] = profile
        logger.debug("Registered model: %s", profile.model_id)

    def add_rule(self, rule: RoutingRule) -> None:
        self._rules[rule.task_type] = rule
        logger.debug("Added rule for task_type: %s", rule.task_type)

    def route(
        self,
        task_type: str,
        context_budget: int = 4096,
        prefer_local: bool = False,
    ) -> str | None:
        rule = self._rules.get(task_type)
        if rule is None:
            logger.warning("No routing rule for task_type=%s", task_type)
            return None

        scored: list[tuple[float, str]] = []
        for profile in self._profiles.values():
            if profile.max_context < context_budget:
                continue
            avg_cost = (profile.cost_per_1k_input + profile.cost_per_1k_output) / 2
            if avg_cost > rule.max_cost_per_1k_tokens and rule.max_cost_per_1k_tokens > 0:
                continue
            if profile.avg_latency_ms > rule.max_latency_ms:
                continue
            if rule.task_type in ("scan", "exploit") and not profile.supports_tools:
                continue
            score = self.score_model(profile, rule, prefer_local)
            scored.append((score, profile.model_id))

        if not scored:
            for fallback_id in rule.fallback_models:
                if fallback_id in self._profiles:
                    logger.info("Using fallback model: %s", fallback_id)
                    return fallback_id
            logger.warning("No models available for task_type=%s", task_type)
            return None

        scored.sort(key=lambda x: x[0], reverse=True)
        best_score, best_id = scored[0]
        logger.info("Routed task_type=%s → %s (score=%.1f)", task_type, best_id, best_score)
        return best_id

    def score_model(
        self,
        profile: ModelProfile,
        rule: RoutingRule,
        prefer_local: bool,
    ) -> float:
        score = 0.0
        cap_set = set(profile.capabilities)

        # Capability match (up to 40 points)
        if rule.preferred_capabilities:
            matches = sum(1 for c in rule.preferred_capabilities if c in cap_set)
            score += (matches / len(rule.preferred_capabilities)) * 40

        # Cost score (up to 25 points) — cheaper is better
        avg_cost = (profile.cost_per_1k_input + profile.cost_per_1k_output) / 2
        if rule.max_cost_per_1k_tokens > 0:
            cost_ratio = avg_cost / rule.max_cost_per_1k_tokens
            score += max(0, 25 * (1 - cost_ratio))

        # Latency score (up to 20 points) — faster is better
        if rule.max_latency_ms > 0:
            latency_ratio = profile.avg_latency_ms / rule.max_latency_ms
            score += max(0, 20 * (1 - latency_ratio))

        # Tool support bonus (up to 10 points)
        if rule.task_type in ("scan", "exploit", "code") and profile.supports_tools:
            score += 10

        # Local preference bonus (up to 5 points)
        if prefer_local and ModelCapability.LOCAL in cap_set:
            score += 5

        # Context headroom bonus (up to 5 points)
        if profile.max_context > 0:
            headroom = (profile.max_context - 4096) / profile.max_context
            score += max(0, min(5, headroom * 5))

        return round(min(100.0, score), 2)

    def get_available_models(self) -> list[ModelProfile]:
        return list(self._profiles.values())

    def estimate_cost(
        self,
        model_id: str,
        input_tokens: int,
        output_tokens: int,
    ) -> float | None:
        profile = self._profiles.get(model_id)
        if profile is None:
            return None
        return (
            profile.cost_per_1k_input * (input_tokens / 1000)
            + profile.cost_per_1k_output * (output_tokens / 1000)
        )


def _build_default_router() -> ModelRouter:
    router = ModelRouter()

    router.add_rule(RoutingRule(
        task_type="scan",
        preferred_capabilities=[ModelCapability.TOOL_USE, ModelCapability.FAST],
        max_cost_per_1k_tokens=0.005,
        max_latency_ms=8000,
    ))
    router.add_rule(RoutingRule(
        task_type="exploit",
        preferred_capabilities=[ModelCapability.TOOL_USE, ModelCapability.REASONING],
        max_cost_per_1k_tokens=0.05,
        max_latency_ms=15000,
    ))
    router.add_rule(RoutingRule(
        task_type="report",
        preferred_capabilities=[ModelCapability.CHAT, ModelCapability.CHEAP],
        max_cost_per_1k_tokens=0.008,
        max_latency_ms=10000,
    ))
    router.add_rule(RoutingRule(
        task_type="reason",
        preferred_capabilities=[ModelCapability.REASONING],
        max_cost_per_1k_tokens=0.03,
        max_latency_ms=12000,
    ))
    router.add_rule(RoutingRule(
        task_type="code",
        preferred_capabilities=[ModelCapability.CODE, ModelCapability.TOOL_USE],
        max_cost_per_1k_tokens=0.02,
        max_latency_ms=10000,
    ))
    router.add_rule(RoutingRule(
        task_type="chat",
        preferred_capabilities=[ModelCapability.CHAT, ModelCapability.FAST, ModelCapability.CHEAP],
        max_cost_per_1k_tokens=0.005,
        max_latency_ms=5000,
    ))

    return router


DEFAULT_ROUTER: ModelRouter = _build_default_router()


def route_task(task_type: str, **kwargs) -> str | None:
    return DEFAULT_ROUTER.route(task_type, **kwargs)
