from __future__ import annotations

import logging
from collections import defaultdict

from plugins.ares.config import get_config

logger = logging.getLogger(__name__)


class DoomLoopDetector:
    def __init__(self):
        self._counts: dict = defaultdict(int)
        self._last_reset_turn: str = ""

    def _freeze_args(self, args: dict) -> tuple:
        if not args:
            return ()
        return tuple(sorted((k, str(v)) for k, v in args.items() if k != "task_id"))

    def check(self, tool_name: str, args: dict, turn_id: str = None) -> bool:
        if turn_id and turn_id != self._last_reset_turn:
            self._counts.clear()
            self._last_reset_turn = turn_id
        key = (tool_name, self._freeze_args(args))
        self._counts[key] += 1
        return self._counts[key]

    def reset(self):
        self._counts.clear()


_detector = DoomLoopDetector()


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
    threshold = cfg.safety_doom_loop_threshold
    if threshold <= 0:
        return None
    count = _detector.check(tool_name, args, turn_id)
    if count <= threshold:
        return None
    logger.warning(
        "Doom loop detected: tool=%s called %d times with same args "
        "session=%s turn=%s",
        tool_name, count, session_id, turn_id,
    )
    return {
        "action": "block",
        "message": (
            f"Tool `{tool_name}` has been called {count} times with the same "
            f"arguments (threshold: {threshold}). This appears to be a loop. "
            f"Try a different approach or target."
        ),
    }
