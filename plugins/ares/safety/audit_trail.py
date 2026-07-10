from __future__ import annotations

import datetime
import json
import logging
import os
from pathlib import Path
from typing import Optional

from plugins.ares.config import get_config

logger = logging.getLogger(__name__)


class AuditTrail:
    def __init__(self):
        self._session_logs: dict = {}
        self._audit_dir = None

    def _get_audit_dir(self) -> Path:
        if self._audit_dir is None:
            base = Path(os.getenv("CYBERFOX_HOME") or Path.home() / ".cyberfox")
            self._audit_dir = base / "logs"
            self._audit_dir.mkdir(parents=True, exist_ok=True)
        return self._audit_dir

    def _get_log_path(self, session_id: str) -> Path:
        return self._get_audit_dir() / f"session_{session_id}.jsonl"

    def log(
        self,
        tool_name: str,
        args: dict,
        result: str = None,
        session_id: str = None,
        tool_call_id: str = None,
        turn_id: str = None,
        task_id: str = None,
    ):
        cfg = get_config()
        if not cfg.safety_log_all_commands:
            return
        if not session_id:
            return
        entry = {
            "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
            "session_id": session_id,
            "turn_id": turn_id,
            "tool_call_id": tool_call_id,
            "tool": tool_name,
            "args": self._sanitize_args(tool_name, args),
            "result_summary": self._summarize_result(result),
        }
        log_path = self._get_log_path(session_id)
        try:
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry) + "\n")
        except OSError as e:
            logger.warning("Failed to write audit log: %s", e)

    def _sanitize_args(self, tool_name: str, args: dict) -> dict:
        sensitive_keys = {"password", "pass", "secret", "token", "api_key", "auth"}
        sanitized = {}
        for k, v in args.items():
            if any(s in k.lower() for s in sensitive_keys):
                sanitized[k] = "***REDACTED***"
            else:
                sanitized[k] = v
        return sanitized

    def _summarize_result(self, result: Optional[str]) -> str:
        if not result:
            return ""
        if len(result) > 500:
            return result[:500] + "..."
        return result

    def on_session_end(self, session_id: str = None, completed: bool = None, **kwargs):
        if not session_id:
            return
        end_entry = {
            "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
            "session_id": session_id,
            "event": "session_end",
            "completed": completed,
        }
        log_path = self._get_log_path(session_id)
        try:
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(end_entry) + "\n")
        except OSError as e:
            logger.warning("Failed to write session end audit entry: %s", e)


_audit = AuditTrail()


def post_tool_call(
    tool_name: str,
    args: dict = None,
    result: str = None,
    task_id: str = None,
    session_id: str = None,
    tool_call_id: str = None,
    turn_id: str = None,
    **kwargs,
):
    if args is None:
        args = {}
    _audit.log(tool_name, args, result, session_id, tool_call_id, turn_id, task_id)


def on_session_end(session_id: str = None, completed: bool = None, **kwargs):
    _audit.on_session_end(session_id, completed)
