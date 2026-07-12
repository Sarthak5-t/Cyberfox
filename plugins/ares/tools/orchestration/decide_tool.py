from __future__ import annotations

from plugins.ares.tools.base import json_result
from plugins.ares.state import engagement_store as store

TOOLSET = "ares_utility"


def _handle_decide(args: dict, **kw) -> str:
    eng = store.get_engagement()
    if not eng:
        return json_result(False, error="No active engagement. Call engage_init first.")
    reasoning = args.get("reasoning", "")
    action = args.get("action", "")
    if not reasoning or not action:
        return json_result(False, error="reasoning and action are required")
    context = args.get("context")
    tool_call_id = args.get("tool_call_id")
    did = store.add_decision(
        engagement_id=eng.id,
        reasoning=reasoning,
        action=action,
        context=context,
        tool_call_id=tool_call_id,
    )
    return json_result(True, data={"decision_id": did, "logged": True})


_SCHEMA = {
    "name": "decide",
    "description": "Log a decision with reasoning. Use this whenever you change approach, choose between options, or make a significant decision. Records WHY you did WHAT so the engagement history is complete.",
    "parameters": {
        "type": "object",
        "properties": {
            "reasoning": {"type": "string", "description": "WHY this decision — what you observed, what alternatives you considered"},
            "action": {"type": "string", "description": "WHAT you decided to do"},
            "context": {"type": "string", "description": "What prompted this decision (tool output, entity state, etc.)"},
        },
        "required": ["reasoning", "action"],
    },
}


def register_tools(ctx) -> None:
    ctx.register_tool(
        name="decide",
        toolset=TOOLSET,
        schema=_SCHEMA,
        handler=lambda args, **kw: _handle_decide(args, **kw),
        emoji="🤔",
    )
