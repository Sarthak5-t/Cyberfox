from __future__ import annotations

import logging
from typing import Any, Optional

from plugins.ares.agents.lifecycle import AgentLifecycleManager, get_lifecycle_manager
from plugins.ares.agents.communication import AgentCommunicationBus, get_communication_bus
from plugins.ares.agents.router import TaskSpecializationRouter, get_router
from plugins.ares.agents.checkpoint import AgentCheckpointManager, get_checkpoint_manager

from plugins.ares.memory.manager import MemoryManager, get_memory_manager

from plugins.ares.skills.hub import SkillHub, get_skill_hub
from plugins.ares.skills.scoring import SkillScorer, get_skill_scorer

from plugins.ares.reasoning.adaptive import AdaptiveThinkingEngine, get_adaptive_engine
from plugins.ares.reasoning.chains import ReasoningChainBuilder, get_reasoning_chains
from plugins.ares.reasoning.planning import ContextAwarePlanner, get_context_planner
from plugins.ares.reasoning.decisions import DecisionFramework, get_decision_framework

from plugins.ares.os_interaction.process import ProcessManager, get_process_manager
from plugins.ares.os_interaction.shell import EnhancedShell, get_enhanced_shell
from plugins.ares.os_interaction.sandbox import SecuritySandbox, get_security_sandbox
from plugins.ares.os_interaction.monitor import SystemMonitor, get_system_monitor

from plugins.ares.bugbounty.rate_limiter import RateLimiter, get_rate_limiter
from plugins.ares.bugbounty.scope_enforcer import ScopeEnforcer, get_scope_enforcer
from plugins.ares.bugbounty.opsec import OPSEC, get_opsec
from plugins.ares.bugbounty.waf_advisor import WAFAdvisor, get_waf_advisor
from plugins.ares.bugbounty.proxy_manager import ProxyManager, get_proxy_manager
from plugins.ares.bugbounty.auth_handler import AuthHandler, get_auth_handler
from plugins.ares.bugbounty.vuln_validator import VulnValidator, get_vuln_validator
from plugins.ares.bugbounty.orchestrator import BugBountyOrchestrator, get_orchestrator
from plugins.ares.bugbounty.platform_api import HackerOneAPI, get_hackerone

logger = logging.getLogger(__name__)


class AresAgenticAPI:
    """Unified API for all Ares agentic capabilities."""

    def __init__(self):
        self._initialized = False
        self._lifecycle: Optional[AgentLifecycleManager] = None
        self._communication: Optional[AgentCommunicationBus] = None
        self._router: Optional[TaskSpecializationRouter] = None
        self._checkpoint: Optional[AgentCheckpointManager] = None
        self._memory: Optional[MemoryManager] = None
        self._skill_hub: Optional[SkillHub] = None
        self._skill_scorer: Optional[SkillScorer] = None
        self._thinking: Optional[AdaptiveThinkingEngine] = None
        self._reasoning: Optional[ReasoningChainBuilder] = None
        self._planner: Optional[ContextAwarePlanner] = None
        self._decisions: Optional[DecisionFramework] = None
        self._process_mgr: Optional[ProcessManager] = None
        self._shell: Optional[EnhancedShell] = None
        self._sandbox: Optional[SecuritySandbox] = None
        self._monitor: Optional[SystemMonitor] = None
        self._bugbounty_rate_limiter: Optional[RateLimiter] = None
        self._bugbounty_scope: Optional[ScopeEnforcer] = None
        self._bugbounty_opsec: Optional[OPSEC] = None
        self._bugbounty_waf: Optional[WAFAdvisor] = None
        self._bugbounty_proxy: Optional[ProxyManager] = None
        self._bugbounty_auth: Optional[AuthHandler] = None
        self._bugbounty_validator: Optional[VulnValidator] = None
        self._bugbounty_orchestrator: Optional[BugBountyOrchestrator] = None
        self._bugbounty_hackerone: Optional[HackerOneAPI] = None

    def initialize(self) -> None:
        """Initialize all agentic subsystems."""
        if self._initialized:
            logger.warning("AresAgenticAPI already initialized")
            return

        logger.info("Initializing Ares Agentic API...")

        # Initialize subsystems
        self._lifecycle = get_lifecycle_manager()
        self._communication = get_communication_bus()
        self._router = get_router()
        self._checkpoint = get_checkpoint_manager()
        self._memory = get_memory_manager()
        self._skill_hub = get_skill_hub()
        self._skill_scorer = get_skill_scorer()
        self._thinking = get_adaptive_engine()
        self._reasoning = get_reasoning_chains()
        self._planner = get_context_planner()
        self._decisions = get_decision_framework()
        self._process_mgr = get_process_manager()
        self._shell = get_enhanced_shell()
        self._sandbox = get_security_sandbox()
        self._monitor = get_system_monitor()

        # Bug bounty subsystems
        self._bugbounty_rate_limiter = get_rate_limiter()
        self._bugbounty_scope = get_scope_enforcer()
        self._bugbounty_opsec = get_opsec()
        self._bugbounty_waf = get_waf_advisor()
        self._bugbounty_proxy = get_proxy_manager()
        self._bugbounty_auth = get_auth_handler()
        self._bugbounty_validator = get_vuln_validator()
        self._bugbounty_orchestrator = get_orchestrator()
        self._bugbounty_hackerone = get_hackerone()

        self._initialized = True
        logger.info("Ares Agentic API initialized successfully")

    @property
    def agents(self) -> AgentLifecycleManager:
        """Get the agent lifecycle manager."""
        if not self._lifecycle:
            raise RuntimeError("AresAgenticAPI not initialized. Call initialize() first.")
        return self._lifecycle

    @property
    def communication(self) -> AgentCommunicationBus:
        """Get the communication bus."""
        if not self._communication:
            raise RuntimeError("AresAgenticAPI not initialized. Call initialize() first.")
        return self._communication

    @property
    def router(self) -> TaskSpecializationRouter:
        """Get the task router."""
        if not self._router:
            raise RuntimeError("AresAgenticAPI not initialized. Call initialize() first.")
        return self._router

    @property
    def checkpoint(self) -> AgentCheckpointManager:
        """Get the checkpoint manager."""
        if not self._checkpoint:
            raise RuntimeError("AresAgenticAPI not initialized. Call initialize() first.")
        return self._checkpoint

    @property
    def memory(self) -> MemoryManager:
        """Get the memory manager."""
        if not self._memory:
            raise RuntimeError("AresAgenticAPI not initialized. Call initialize() first.")
        return self._memory

    @property
    def skills(self) -> SkillHub:
        """Get the skill hub."""
        if not self._skill_hub:
            raise RuntimeError("AresAgenticAPI not initialized. Call initialize() first.")
        return self._skill_hub

    @property
    def skill_scorer(self) -> SkillScorer:
        """Get the skill scorer."""
        if not self._skill_scorer:
            raise RuntimeError("AresAgenticAPI not initialized. Call initialize() first.")
        return self._skill_scorer

    @property
    def thinking(self) -> AdaptiveThinkingEngine:
        """Get the adaptive thinking engine."""
        if not self._thinking:
            raise RuntimeError("AresAgenticAPI not initialized. Call initialize() first.")
        return self._thinking

    @property
    def reasoning(self) -> ReasoningChainBuilder:
        """Get the reasoning chain builder."""
        if not self._reasoning:
            raise RuntimeError("AresAgenticAPI not initialized. Call initialize() first.")
        return self._reasoning

    @property
    def planner(self) -> ContextAwarePlanner:
        """Get the context-aware planner."""
        if not self._planner:
            raise RuntimeError("AresAgenticAPI not initialized. Call initialize() first.")
        return self._planner

    @property
    def decisions(self) -> DecisionFramework:
        """Get the decision framework."""
        if not self._decisions:
            raise RuntimeError("AresAgenticAPI not initialized. Call initialize() first.")
        return self._decisions

    @property
    def process(self) -> ProcessManager:
        """Get the process manager."""
        if not self._process_mgr:
            raise RuntimeError("AresAgenticAPI not initialized. Call initialize() first.")
        return self._process_mgr

    @property
    def shell(self) -> EnhancedShell:
        """Get the enhanced shell."""
        if not self._shell:
            raise RuntimeError("AresAgenticAPI not initialized. Call initialize() first.")
        return self._shell

    @property
    def sandbox(self) -> SecuritySandbox:
        """Get the security sandbox."""
        if not self._sandbox:
            raise RuntimeError("AresAgenticAPI not initialized. Call initialize() first.")
        return self._sandbox

    @property
    def monitor(self) -> SystemMonitor:
        """Get the system monitor."""
        if not self._monitor:
            raise RuntimeError("AresAgenticAPI not initialized. Call initialize() first.")
        return self._monitor

    @property
    def rate_limiter(self) -> RateLimiter:
        """Get the bug bounty rate limiter."""
        if not self._bugbounty_rate_limiter:
            raise RuntimeError("AresAgenticAPI not initialized. Call initialize() first.")
        return self._bugbounty_rate_limiter

    @property
    def scope(self) -> ScopeEnforcer:
        """Get the bug bounty scope enforcer."""
        if not self._bugbounty_scope:
            raise RuntimeError("AresAgenticAPI not initialized. Call initialize() first.")
        return self._bugbounty_scope

    @property
    def opsec(self) -> OPSEC:
        """Get the bug bounty OPSEC layer."""
        if not self._bugbounty_opsec:
            raise RuntimeError("AresAgenticAPI not initialized. Call initialize() first.")
        return self._bugbounty_opsec

    @property
    def waf(self) -> WAFAdvisor:
        """Get the WAF advisor."""
        if not self._bugbounty_waf:
            raise RuntimeError("AresAgenticAPI not initialized. Call initialize() first.")
        return self._bugbounty_waf

    @property
    def proxy(self) -> ProxyManager:
        """Get the bug bounty proxy manager."""
        if not self._bugbounty_proxy:
            raise RuntimeError("AresAgenticAPI not initialized. Call initialize() first.")
        return self._bugbounty_proxy

    @property
    def auth(self) -> AuthHandler:
        """Get the bug bounty auth handler."""
        if not self._bugbounty_auth:
            raise RuntimeError("AresAgenticAPI not initialized. Call initialize() first.")
        return self._bugbounty_auth

    @property
    def validator(self) -> VulnValidator:
        """Get the bug bounty vuln validator."""
        if not self._bugbounty_validator:
            raise RuntimeError("AresAgenticAPI not initialized. Call initialize() first.")
        return self._bugbounty_validator

    @property
    def orchestrator(self) -> BugBountyOrchestrator:
        """Get the bug bounty pipeline orchestrator."""
        if not self._bugbounty_orchestrator:
            raise RuntimeError("AresAgenticAPI not initialized. Call initialize() first.")
        return self._bugbounty_orchestrator

    @property
    def hackerone(self) -> HackerOneAPI:
        """Get the HackerOne API client."""
        if not self._bugbounty_hackerone:
            raise RuntimeError("AresAgenticAPI not initialized. Call initialize() first.")
        return self._bugbounty_hackerone

    def get_statistics(self) -> dict[str, Any]:
        """Get comprehensive statistics across all subsystems."""
        stats = {
            "initialized": self._initialized,
        }

        if self._initialized:
            # Gather stats from each subsystem, tolerating missing methods
            agent_stats = {}
            try:
                agents = self._lifecycle.list_agents() if hasattr(self._lifecycle, 'list_agents') else []
                agent_stats = {"total_agents": len(agents)}
            except Exception:
                agent_stats = {"total_agents": 0}

            memory_stats = {}
            try:
                memory_stats = self._memory.get_memory_stats()
            except Exception:
                memory_stats = {}

            stats.update({
                "agents": agent_stats,
                "memory": memory_stats,
                "skills": self._skill_hub.get_statistics() if hasattr(self._skill_hub, 'get_statistics') else {},
                "reasoning": self._reasoning.get_statistics() if hasattr(self._reasoning, 'get_statistics') else {},
                "planning": self._planner.get_statistics() if hasattr(self._planner, 'get_statistics') else {},
                "decisions": self._decisions.get_statistics() if hasattr(self._decisions, 'get_statistics') else {},
                "process": self._process_mgr.get_statistics() if hasattr(self._process_mgr, 'get_statistics') else {},
                "shell": self._shell.get_statistics() if hasattr(self._shell, 'get_statistics') else {},
                "sandbox": self._sandbox.get_statistics() if hasattr(self._sandbox, 'get_statistics') else {},
                "monitor": self._monitor.get_statistics() if hasattr(self._monitor, 'get_statistics') else {},
            })

        return stats

    def shutdown(self) -> None:
        """Shutdown all agentic subsystems."""
        if not self._initialized:
            return

        logger.info("Shutting down Ares Agentic API...")

        # Cleanup sandboxes
        for sandbox in self._sandbox.list_sandboxes():
            self._sandbox.destroy_sandbox(sandbox.config.sandbox_id)

        # Stop running processes
        for proc in self._process_mgr.list_processes(status="running"):
            self._process_mgr.stop_process(proc.process_id)

        self._initialized = False
        logger.info("Ares Agentic API shut down")


# Global singleton
_agentic_api: Optional[AresAgenticAPI] = None


def get_agentic_api() -> AresAgenticAPI:
    """Get the global AresAgenticAPI instance."""
    global _agentic_api
    if _agentic_api is None:
        _agentic_api = AresAgenticAPI()
        _agentic_api.initialize()
    return _agentic_api


def reset_agentic_api() -> None:
    """Reset the global AresAgenticAPI instance."""
    global _agentic_api
    if _agentic_api:
        _agentic_api.shutdown()
    _agentic_api = None
