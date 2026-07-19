from __future__ import annotations

from plugins.ares.tools.base import check_binary, run_command, truncate_output, json_result, extract_target
from plugins.ares.tools.permission import (
    PermissionLevel,
    ToolCategory,
    ToolScope,
    ToolTimeout,
    ToolProtocol,
    AresTool,
    get_tool_permission,
    ARES_TOOL_PERMISSIONS,
)
from plugins.ares.tools.tokenjuice import compress, compress_then_truncate, detect_kind, estimate_tokens
from plugins.ares.tools.sandbox import ToolSandbox, JailSpec, JailResult, sandbox_subprocess
from plugins.ares.tools.router import ModelRouter, route_task, DEFAULT_ROUTER
from plugins.ares.tools.secrets import SecretStore, ARES_SECRETS, get_secret, set_secret
from plugins.ares.tools.council import ModelCouncil, ARES_COUNCIL, deliberate
from plugins.ares.tools.memory_tree import MemoryTree, ARES_MEMORY, ingest_output

__all__ = [
    # base
    "check_binary", "run_command", "truncate_output", "json_result", "extract_target",
    # permission / governance
    "PermissionLevel", "ToolCategory", "ToolScope", "ToolTimeout",
    "ToolProtocol", "AresTool", "get_tool_permission", "ARES_TOOL_PERMISSIONS",
    # token juice
    "compress", "compress_then_truncate", "detect_kind", "estimate_tokens",
    # sandbox
    "ToolSandbox", "JailSpec", "JailResult", "sandbox_subprocess",
    # router
    "ModelRouter", "route_task", "DEFAULT_ROUTER",
    # secrets
    "SecretStore", "ARES_SECRETS", "get_secret", "set_secret",
    # council
    "ModelCouncil", "ARES_COUNCIL", "deliberate",
    # memory tree
    "MemoryTree", "ARES_MEMORY", "ingest_output",
]
