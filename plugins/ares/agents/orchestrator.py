from __future__ import annotations

import json
import logging

from plugins.ares.tools.base import json_result
from plugins.ares.agents import AGENT_DEFINITIONS

logger = logging.getLogger(__name__)

TOOLSET = "ares_utility"


def _handle(args: dict, **kw) -> str:
    role = args.get("role", "lead_orchestrator")
    action = args.get("action", "assign")
    goal = args.get("goal", "")
    context = args.get("context", "")
    if role not in AGENT_DEFINITIONS:
        return json_result(False, error=f"Unknown role: {role}. Available: {list(AGENT_DEFINITIONS.keys())}")
    agent_def = AGENT_DEFINITIONS[role]

    parent_agent = kw.get("parent_agent")
    if parent_agent:
        try:
            from tools.delegate_tool import delegate_task as _delegate_task
            full_context = (
                f"Role: {agent_def['description']}\n"
                f"Allowed toolsets: {', '.join(agent_def['allowed_toolsets'])}\n\n"
                f"{context}"
            )
            result = _delegate_task(
                goal=goal,
                context=full_context,
                role="leaf",
                background=False,
                parent_agent=parent_agent,
            )
            return result if isinstance(result, str) else json_result(True, data=result)
        except ImportError:
            logger.warning("delegate_task not available, returning task definition only")
        except Exception as e:
            logger.error(f"Delegation failed: {e}")
            return json_result(False, error=f"Delegation failed: {e}")

    payload = {
        "action": action,
        "role": role,
        "description": agent_def["description"],
        "allowed_toolsets": agent_def["allowed_toolsets"],
        "goal": goal,
        "context": context,
        "note": "delegate_task unavailable — call delegate_task manually with this goal/context",
    }
    return json_result(True, data=payload)


SCHEMA = {
    "name": "ares_delegate",
    "description": "Define a sub-task for a specialist agent role. Returns a task definition that can be passed to delegate_task. Supports pentester (recon/exploit), soc_analyst (analysis/reporting), and lead_orchestrator (coordination). Approval gate: requires user confirmation before execution.",
    "parameters": {
        "type": "object",
        "properties": {
            "role": {
                "type": "string",
                "enum": list(AGENT_DEFINITIONS.keys()),
                "default": "lead_orchestrator",
                "description": "Agent role to assign the task to",
            },
            "action": {
                "type": "string",
                "enum": ["assign", "report", "escalate"],
                "default": "assign",
                "description": "Action type: assign (new task), report (summarize findings), escalate (flag for review)",
            },
            "goal": {"type": "string", "description": "Clear description of what needs to be done"},
            "context": {"type": "string", "description": "Context, findings, or data the specialist needs to work with"},
        },
        "required": ["role", "goal"],
    },
}


def register_tools(ctx) -> None:
    ctx.register_tool(
        name="ares_delegate",
        toolset=TOOLSET,
        schema=SCHEMA,
        handler=lambda args, **kw: _handle(args, **kw),
        emoji="🎯",
    )
