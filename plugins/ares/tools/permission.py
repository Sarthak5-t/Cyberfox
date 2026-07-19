"""Tool governance system for Ares — ported from OpenHuman's tool/traits.rs.

Provides PermissionLevel, ToolScope, ToolCategory, ToolTimeout, and a
ToolProtocol that Ares tools can implement for formal governance.
"""
from __future__ import annotations

import enum
import json
from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable


# ── Enums (ported from OpenHuman PermissionLevel, ToolScope, ToolCategory) ──

class PermissionLevel(enum.IntEnum):
    """Permission level required to execute a tool.

    Channels/engagements set a maximum permission level. Tools requiring
    a level above the maximum are rejected before execution.
    """
    NONE = 0       # Metadata-only (no side effects)
    READ_ONLY = 1  # Read-only ops (scans, whois, DNS lookups)
    WRITE = 2      # Write ops (save findings, write files)
    EXECUTE = 3    # Command execution (shell, scripts, scanners)
    DANGEROUS = 4  # Exploitation, credential attacks, system-level


class ToolScope(enum.Enum):
    """Where a tool is available."""
    ALL = "all"            # Agent loop, CLI, and RPC
    AGENT_ONLY = "agent"   # Only in autonomous agent loop
    CLI_ONLY = "cli"       # Only via CLI/RPC invocation


class ToolCategory(enum.Enum):
    """Category of a tool — scoping for sub-agent tool visibility."""
    SECURITY = "security"       # Built-in Ares security tools
    RECON = "recon"             # Reconnaissance tools
    SCANNING = "scanning"       # Vulnerability scanning tools
    EXPLOITATION = "exploitation"  # Exploitation tools
    AD = "ad"                   # Active Directory tools
    BROWSING = "browsing"       # Web browsing tools
    UTILITY = "utility"         # Utility / findings / journal tools
    EXTERNAL = "external"       # External integration tools


class ToolTimeout(enum.Enum):
    """How to bound a single tool invocation."""
    INHERIT = "inherit"    # Use global timeout (default)
    UNBOUNDED = "unbounded"  # No deadline (long-running scans)
    CUSTOM = "custom"      # Explicit timeout in seconds


# ── Data classes ──

@dataclass
class ToolCallOptions:
    """Per-invocation options from the agent loop."""
    prefer_markdown: bool = False
    timeout_secs: int | None = None


@dataclass
class ToolSpec:
    """LLM-facing tool description."""
    name: str
    description: str
    parameters: dict[str, Any] = field(default_factory=dict)


@dataclass
class ToolPolicyDecision:
    """Result of a tool policy check."""
    allowed: bool
    reason: str = ""
    requires_approval: bool = False


# ── Tool Protocol (ported from OpenHuman Tool trait) ──

@runtime_checkable
class ToolProtocol(Protocol):
    """Protocol that Ares tools can implement for formal governance.

    Tools that don't implement this protocol still work via the legacy
    base.py path, but tools that implement it get permission gating,
    timeout enforcement, and approval routing.
    """

    def name(self) -> str:
        """Tool name used in LLM function calling."""
        ...

    def description(self) -> str:
        """Human-readable description."""
        ...

    def permission_level(self) -> PermissionLevel:
        """Permission level required. Default: READ_ONLY."""
        ...

    def external_effect(self) -> bool:
        """Whether this tool produces externally-observable side effects.
        When True, the approval gate intercepts before execution."""
        ...

    def category(self) -> ToolCategory:
        """Tool category for sub-agent scoping."""
        ...

    def scope(self) -> ToolScope:
        """Where this tool is available."""
        ...

    def timeout_policy(self, args: dict | None = None) -> tuple[ToolTimeout, int | None]:
        """Return (timeout_type, optional_secs)."""
        ...

    def execute(self, args: dict[str, Any]) -> str:
        """Execute the tool. Returns JSON result string."""
        ...


# ── Default implementations for non-Protocol tools ──

@dataclass
class AresTool:
    """Base dataclass for tools that want governance but don't need
    full Protocol compliance. Provides sensible defaults."""
    _name: str = ""
    _description: str = ""
    _permission_level: PermissionLevel = PermissionLevel.READ_ONLY
    _external_effect: bool = False
    _category: ToolCategory = ToolCategory.SECURITY
    _scope: ToolScope = ToolScope.ALL
    _timeout_type: ToolTimeout = ToolTimeout.INHERIT
    _timeout_secs: int | None = None

    def get_name(self) -> str:
        return self._name

    def get_description(self) -> str:
        return self._description

    def get_permission_level(self) -> PermissionLevel:
        return self._permission_level

    def is_external_effect(self) -> bool:
        return self._external_effect

    def get_category(self) -> ToolCategory:
        return self._category

    def get_scope(self) -> ToolScope:
        return self._scope

    def get_timeout(self, args: dict | None = None) -> tuple[ToolTimeout, int | None]:
        return self._timeout_type, self._timeout_secs


# ── Pre-defined Ares tool permission map ──
# Maps tool names → (PermissionLevel, external_effect, category, timeout_secs)
# Based on the existing _EXPLOIT_TOOLS in approval_hardening.py + scan tools

ARES_TOOL_PERMISSIONS: dict[str, tuple[PermissionLevel, bool, ToolCategory, int | None]] = {
    # Recon — read-only, no external effect
    "nmap_scan":          (PermissionLevel.EXECUTE, False, ToolCategory.RECON, 600),
    "dnsrecon_scan":      (PermissionLevel.EXECUTE, False, ToolCategory.RECON, 300),
    "subdomain_enum":     (PermissionLevel.EXECUTE, False, ToolCategory.RECON, 300),
    "masscan_scan":       (PermissionLevel.EXECUTE, False, ToolCategory.RECON, 600),
    "amass_scan":         (PermissionLevel.EXECUTE, False, ToolCategory.RECON, 900),
    "whois_scan":         (PermissionLevel.READ_ONLY, False, ToolCategory.RECON, 60),
    "theharvester_scan":  (PermissionLevel.EXECUTE, False, ToolCategory.RECON, 300),
    "whatweb_scan":       (PermissionLevel.EXECUTE, False, ToolCategory.RECON, 120),

    # Scanning — execute, no external effect
    "nuclei_scan":        (PermissionLevel.EXECUTE, False, ToolCategory.SCANNING, 600),
    "gobuster_scan":      (PermissionLevel.EXECUTE, False, ToolCategory.SCANNING, 600),
    "feroxbuster_scan":   (PermissionLevel.EXECUTE, False, ToolCategory.SCANNING, 600),
    "ffuf_scan":          (PermissionLevel.EXECUTE, False, ToolCategory.SCANNING, 600),
    "wfuzz_scan":         (PermissionLevel.EXECUTE, False, ToolCategory.SCANNING, 600),
    "nikto_scan":         (PermissionLevel.EXECUTE, False, ToolCategory.SCANNING, 600),
    "wpscan_scan":        (PermissionLevel.EXECUTE, False, ToolCategory.SCANNING, 600),
    "wafw00f_scan":       (PermissionLevel.READ_ONLY, False, ToolCategory.SCANNING, 120),
    "enum4linux_scan":    (PermissionLevel.EXECUTE, False, ToolCategory.SCANNING, 300),
    "smbclient_tool":     (PermissionLevel.EXECUTE, False, ToolCategory.SCANNING, 120),
    "snmpwalk_tool":      (PermissionLevel.EXECUTE, False, ToolCategory.SCANNING, 300),
    "burp_scan":          (PermissionLevel.EXECUTE, False, ToolCategory.SCANNING, 600),
    "burp_spider":        (PermissionLevel.EXECUTE, False, ToolCategory.SCANNING, 600),
    "burp_repeater":      (PermissionLevel.EXECUTE, False, ToolCategory.SCANNING, 120),
    "subjack":            (PermissionLevel.EXECUTE, False, ToolCategory.SCANNING, 600),

    # Exploitation — dangerous, external effect = True
    "searchsploit_tool":  (PermissionLevel.EXECUTE, False, ToolCategory.EXPLOITATION, 120),
    "sqlmap_scan":        (PermissionLevel.DANGEROUS, True, ToolCategory.EXPLOITATION, 900),
    "hydra_brute":        (PermissionLevel.DANGEROUS, True, ToolCategory.EXPLOITATION, 900),
    "msf_exec":           (PermissionLevel.DANGEROUS, True, ToolCategory.EXPLOITATION, 600),
    "msf_console":        (PermissionLevel.DANGEROUS, True, ToolCategory.EXPLOITATION, 600),
    "msf_search":         (PermissionLevel.READ_ONLY, False, ToolCategory.EXPLOITATION, 120),
    "msf_payload":        (PermissionLevel.DANGEROUS, True, ToolCategory.EXPLOITATION, 120),
    "msf_post":           (PermissionLevel.DANGEROUS, True, ToolCategory.EXPLOITATION, 600),
    "responder_listener": (PermissionLevel.DANGEROUS, True, ToolCategory.EXPLOITATION, 600),
    "exploit_chain":      (PermissionLevel.DANGEROUS, True, ToolCategory.EXPLOITATION, 900),
    "payload_gen":        (PermissionLevel.DANGEROUS, True, ToolCategory.EXPLOITATION, 120),
    "exploit_dev":        (PermissionLevel.DANGEROUS, True, ToolCategory.EXPLOITATION, 600),
    "curl_tool":          (PermissionLevel.READ_ONLY, False, ToolCategory.EXPLOITATION, 60),

    # Active Directory — dangerous, external effect
    "bloodhound_ingest":  (PermissionLevel.DANGEROUS, True, ToolCategory.AD, 600),
    "certipy_find":       (PermissionLevel.EXECUTE, False, ToolCategory.AD, 300),
    "certipy_tool":       (PermissionLevel.DANGEROUS, True, ToolCategory.AD, 600),
    "crackmapexec":       (PermissionLevel.DANGEROUS, True, ToolCategory.AD, 600),
    "kerbrute_enum":      (PermissionLevel.EXECUTE, False, ToolCategory.AD, 600),
    "impacket_exec":      (PermissionLevel.DANGEROUS, True, ToolCategory.AD, 600),

    # Browsing — execute, no external effect
    "browse_autonomously": (PermissionLevel.READ_ONLY, False, ToolCategory.BROWSING, 120),

    # Utility — read-only
    "findings_save":      (PermissionLevel.WRITE, False, ToolCategory.UTILITY, 30),
    "findings_query":     (PermissionLevel.READ_ONLY, False, ToolCategory.UTILITY, 30),
    "findings_update":    (PermissionLevel.WRITE, False, ToolCategory.UTILITY, 30),
    "findings_stats":     (PermissionLevel.READ_ONLY, False, ToolCategory.UTILITY, 30),
    "journal_init":       (PermissionLevel.WRITE, False, ToolCategory.UTILITY, 30),
    "journal_write":      (PermissionLevel.WRITE, False, ToolCategory.UTILITY, 30),
    "journal_read":       (PermissionLevel.READ_ONLY, False, ToolCategory.UTILITY, 30),
    "ares_delegate":      (PermissionLevel.DANGEROUS, True, ToolCategory.UTILITY, 600),
}


def get_tool_permission(tool_name: str) -> tuple[PermissionLevel, bool, ToolCategory, int | None]:
    """Look up the permission tuple for a known Ares tool.

    Returns (permission_level, external_effect, category, timeout_secs).
    Unknown tools default to EXECUTE + not external + SECURITY category.
    """
    return ARES_TOOL_PERMISSIONS.get(
        tool_name,
        (PermissionLevel.EXECUTE, False, ToolCategory.SECURITY, 300),
    )
