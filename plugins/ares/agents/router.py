from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from typing import Any, Optional
from enum import Enum

logger = logging.getLogger(__name__)


class TaskType(Enum):
    """Types of tasks that can be routed."""
    RECON = "recon"
    SCANNING = "scanning"
    EXPLOITATION = "exploitation"
    WEB_ATTACK = "web_attack"
    AD_ATTACK = "ad_attack"
    PRIVILEGE_ESCALATION = "privilege_escalation"
    CLOUD_SECURITY = "cloud_security"
    MOBILE_SECURITY = "mobile_security"
    WIRELESS_SECURITY = "wireless_security"
    SOCIAL_ENGINEERING = "social_engineering"
    MALWARE_ANALYSIS = "malware_analysis"
    REPORTING = "reporting"
    COORDINATION = "coordination"


class TaskPriority(Enum):
    """Task priority levels."""
    LOW = 0
    NORMAL = 1
    HIGH = 2
    CRITICAL = 3


@dataclass
class TaskSpec:
    """Specification for a task."""
    task_type: TaskType
    goal: str
    context: str
    target: str
    priority: TaskPriority = TaskPriority.NORMAL
    required_toolsets: list[str] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class RoutingDecision:
    """Decision about how to route a task."""
    task_type: TaskType
    assigned_role: str
    confidence: float
    reasoning: str
    alternative_roles: list[str] = field(default_factory=list)


class TaskSpecializationRouter:
    """Routes tasks to specialized agents based on task content."""

    def __init__(self):
        self._role_capabilities: dict[str, list[TaskType]] = {
            "pentester": [TaskType.RECON, TaskType.SCANNING, TaskType.EXPLOITATION],
            "osint_analyst": [TaskType.RECON],
            "web_attacker": [TaskType.WEB_ATTACK, TaskType.SCANNING],
            "ad_specialist": [TaskType.AD_ATTACK, TaskType.PRIVILEGE_ESCALATION],
            "privesc_specialist": [TaskType.PRIVILEGE_ESCALATION],
            "cloud_specialist": [TaskType.CLOUD_SECURITY],
            "mobile_specialist": [TaskType.MOBILE_SECURITY],
            "wireless_specialist": [TaskType.WIRELESS_SECURITY],
            "social_engineer": [TaskType.SOCIAL_ENGINEERING],
            "malware_analyst": [TaskType.MALWARE_ANALYSIS],
            "soc_analyst": [TaskType.REPORTING],
            "lead_orchestrator": [TaskType.COORDINATION, TaskType.REPORTING],
            "swarm_recon": [TaskType.RECON],
            "swarm_web": [TaskType.WEB_ATTACK, TaskType.SCANNING],
            "swarm_network": [TaskType.SCANNING],
            "swarm_ad": [TaskType.AD_ATTACK],
            "swarm_exploit": [TaskType.EXPLOITATION],
        }

        self._keyword_patterns: dict[TaskType, list[str]] = {
            TaskType.RECON: [
                r"\b(recon|reconnaissance|enumerate|discovery|fingerprint)\b",
                r"\b(nmap|masscan|subfinder|amass|whois|dnsrecon)\b",
                r"\b(subdomain|dns|port\s*scan)\b",
            ],
            TaskType.SCANNING: [
                r"\b(scan|scanning|vulnerability\s*scan|vuln\s*scan)\b",
                r"\b(nuclei|nikto|gobuster|ffuf|wfuzz|enum4linux)\b",
                r"\b(service\s*detect|version\s*detect)\b",
            ],
            TaskType.EXPLOITATION: [
                r"\b(exploit|exploitation|attack|compromise)\b",
                r"\b(metasploit|searchsploit|sqlmap|hydra)\b",
                r"\b(payload|shellcode|reverse\s*shell)\b",
            ],
            TaskType.WEB_ATTACK: [
                r"\b(web|http|https|website|webapp)\b",
                r"\b(xss|sqli|ssrf|csrf|lfi|rfi)\b",
                r"\b(owasp|injection|authentication\s*bypass)\b",
            ],
            TaskType.AD_ATTACK: [
                r"\b(active\s*directory|ad|domain|kerberos)\b",
                r"\b(kerberoast|asrep|dcsync|golden\s*ticket|silver\s*ticket)\b",
                r"\b(bloodhound|certipy|crackmapexec|impacket)\b",
            ],
            TaskType.PRIVILEGE_ESCALATION: [
                r"\b(privesc|privilege\s*escalation|escalat)\b",
                r"\b(sudo|suid|capabilities|kernel\s*exploit)\b",
                r"\b(root|admin|system)\b",
            ],
            TaskType.CLOUD_SECURITY: [
                r"\b(cloud|aws|azure|gcp|kubernetes|docker)\b",
                r"\b(iam|s3|ec2|lambda|eks|aks|gke)\b",
                r"\b(container|registry|misconfiguration)\b",
            ],
            TaskType.MOBILE_SECURITY: [
                r"\b(mobile|android|ios|apk|ipa)\b",
                r"\b(frida|jadx|apktool|objection)\b",
                r"\b(mobile\s*app|mobile\s*security)\b",
            ],
            TaskType.WIRELESS_SECURITY: [
                r"\b(wireless|wifi|wlan|802\.11)\b",
                r"\b(aircrack|kismet|reaver|wifite)\b",
                r"\b(rogue\s*ap|evil\s*twin|deauth)\b",
            ],
            TaskType.SOCIAL_ENGINEERING: [
                r"\b(social\s*engineer|phishing|pretexting)\b",
                r"\b(spearphish|vishing|smishing)\b",
                r"\b(human\s*factor|awareness)\b",
            ],
            TaskType.MALWARE_ANALYSIS: [
                r"\b(malware|virus|trojan|ransomware)\b",
                r"\b(reverse\s*engineer|disassembl|decompil)\b",
                r"\b(analysis|detonation|sandbox)\b",
            ],
            TaskType.REPORTING: [
                r"\b(report|document|summary|findings)\b",
                r"\b(presentation|executive\s*summary)\b",
                r"\b(deliverable|output|result)\b",
            ],
        }

    def classify_task(self, goal: str, context: str = "") -> TaskType:
        """Classify a task based on its content."""
        text = f"{goal} {context}".lower()
        scores: dict[TaskType, float] = {}

        for task_type, patterns in self._keyword_patterns.items():
            score = 0.0
            for pattern in patterns:
                matches = re.findall(pattern, text, re.IGNORECASE)
                score += len(matches) * 1.0
            scores[task_type] = score

        if not scores or max(scores.values()) == 0:
            return TaskType.RECON  # Default

        return max(scores, key=scores.get)

    def route_task(self, task: TaskSpec) -> RoutingDecision:
        """Route a task to the most appropriate agent."""
        task_type = task.task_type
        best_role = None
        best_confidence = 0.0
        alternatives = []

        for role, capabilities in self._role_capabilities.items():
            if task_type in capabilities:
                # Calculate confidence based on capability match
                capability_score = capabilities.count(task_type) / len(capabilities)
                
                # Check toolset overlap
                toolset_overlap = 0.0
                if task.required_toolsets:
                    role_toolsets = self._get_role_toolsets(role)
                    overlap = set(task.required_toolsets) & set(role_toolsets)
                    toolset_overlap = len(overlap) / len(task.required_toolsets) if task.required_toolsets else 0

                confidence = (capability_score * 0.7) + (toolset_overlap * 0.3)

                if confidence > best_confidence:
                    if best_role:
                        alternatives.append(best_role)
                    best_role = role
                    best_confidence = confidence
                elif confidence > 0:
                    alternatives.append(role)

        if not best_role:
            best_role = "pentester"
            best_confidence = 0.5

        reasoning = self._generate_reasoning(task, best_role, best_confidence)

        return RoutingDecision(
            task_type=task_type,
            assigned_role=best_role,
            confidence=best_confidence,
            reasoning=reasoning,
            alternative_roles=alternatives[:3],
        )

    def _get_role_toolsets(self, role: str) -> list[str]:
        """Get toolsets for a role from AGENT_DEFINITIONS."""
        try:
            from plugins.ares.agents import AGENT_DEFINITIONS
            agent_def = AGENT_DEFINITIONS.get(role, {})
            return agent_def.get("allowed_toolsets", [])
        except ImportError:
            return []

    def _generate_reasoning(
        self,
        task: TaskSpec,
        assigned_role: str,
        confidence: float,
    ) -> str:
        """Generate reasoning for the routing decision."""
        task_type_desc = task.task_type.value.replace("_", " ")
        
        if confidence > 0.8:
            strength = "strong"
        elif confidence > 0.6:
            strength = "moderate"
        else:
            strength = "weak"

        reasoning = (
            f"Task classified as {task_type_desc} based on goal analysis. "
            f"Assigned to {assigned_role} with {strength} confidence ({confidence:.2f}). "
        )

        if task.required_toolsets:
            reasoning += f"Required toolsets: {', '.join(task.required_toolsets)}. "

        if task.dependencies:
            reasoning += f"Depends on: {', '.join(task.dependencies)}. "

        return reasoning

    def build_task_spec(
        self,
        goal: str,
        context: str,
        target: str,
        priority: TaskPriority = TaskPriority.NORMAL,
        dependencies: Optional[list[str]] = None,
    ) -> TaskSpec:
        """Build a task specification from goal and context."""
        task_type = self.classify_task(goal, context)
        
        # Extract required toolsets based on task type
        required_toolsets = self._get_required_toolsets(task_type)

        return TaskSpec(
            task_type=task_type,
            goal=goal,
            context=context,
            target=target,
            priority=priority,
            required_toolsets=required_toolsets,
            dependencies=dependencies or [],
        )

    def _get_required_toolsets(self, task_type: TaskType) -> list[str]:
        """Get required toolsets for a task type."""
        toolset_map = {
            TaskType.RECON: ["ares_recon"],
            TaskType.SCANNING: ["ares_scanning"],
            TaskType.EXPLOITATION: ["ares_exploit"],
            TaskType.WEB_ATTACK: ["ares_scanning", "ares_exploit"],
            TaskType.AD_ATTACK: ["ares_scanning", "ares_ad"],
            TaskType.PRIVILEGE_ESCALATION: ["ares_exploit", "ares_ad"],
            TaskType.CLOUD_SECURITY: ["ares_recon", "ares_scanning", "ares_exploit"],
            TaskType.MOBILE_SECURITY: ["ares_scanning", "ares_exploit"],
            TaskType.WIRELESS_SECURITY: ["ares_recon", "ares_scanning"],
            TaskType.SOCIAL_ENGINEERING: ["ares_recon", "ares_utility"],
            TaskType.MALWARE_ANALYSIS: ["ares_recon", "ares_scanning", "ares_utility"],
            TaskType.REPORTING: ["ares_utility"],
            TaskType.COORDINATION: ["ares_utility", "ares_recon"],
        }
        return toolset_map.get(task_type, ["ares_utility"])

    def get_routing_stats(self) -> dict[str, Any]:
        """Get routing statistics."""
        stats = {
            "roles": len(self._role_capabilities),
            "task_types": len(self._keyword_patterns),
            "capabilities": {
                role: [tt.value for tt in caps]
                for role, caps in self._role_capabilities.items()
            },
        }
        return stats


# Global instance
_router: Optional[TaskSpecializationRouter] = None


def get_router() -> TaskSpecializationRouter:
    """Get the global router instance."""
    global _router
    if _router is None:
        _router = TaskSpecializationRouter()
    return _router
