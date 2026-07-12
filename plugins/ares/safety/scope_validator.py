from __future__ import annotations

import logging

from plugins.ares.config import get_config
from plugins.ares.tools.base import extract_target

logger = logging.getLogger(__name__)


def pre_tool_call(
    tool_name: str,
    args: dict = None,
    task_id: str = None,
    session_id: str = None,
    tool_call_id: str = None,
    turn_id: str = None,
    api_request_id: str = None,
    **kwargs,
):
    if args is None:
        args = {}
    cfg = get_config()
    if cfg.safety_scope_enforcement == "disabled":
        return None
    target = extract_target(args)
    if target is None:
        return None
    if cfg.is_target_in_scope(target):
        return None
    logger.warning(
        "Scope block: tool=%s target=%s session=%s turn=%s",
        tool_name, target, session_id, turn_id,
    )
    return {
        "action": "block",
        "message": (
            f"Target `{target}` is outside the authorized scope. "
            f"Allowed: {cfg.scope}. Update scope file to include this target."
        ),
    }
