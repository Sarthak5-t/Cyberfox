from __future__ import annotations

import datetime
import json
import logging
import os
import re
import shlex
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

_MAX_OUTPUT_LINES = 2000
_MAX_OUTPUT_BYTES = 51200
_TRUNCATION_DIR: Optional[Path] = None

_SAFE_KEY_RE = re.compile(r"^[A-Za-z0-9_./-]+$")
_DANGEROUS_VALUE_RE = re.compile(r"[\n\r\x00`<%]")


def _cyberfox_home() -> Path:
    env = os.getenv("CYBERFOX_HOME")
    if env:
        return Path(env)
    return Path.home() / ".cyberfox"


def _ensure_truncation_dir() -> Path:
    global _TRUNCATION_DIR
    if _TRUNCATION_DIR is None:
        base = _cyberfox_home()
        _TRUNCATION_DIR = base / "ares" / "spill"
        _TRUNCATION_DIR.mkdir(parents=True, exist_ok=True)
    return _TRUNCATION_DIR


def check_binary(name: str) -> bool:
    return shutil.which(name) is not None


def truncate_output(
    output: str,
    max_lines: int = _MAX_OUTPUT_LINES,
    max_bytes: int = _MAX_OUTPUT_BYTES,
) -> tuple[str, Optional[str]]:
    if not output:
        return output, None
    line_count = output.count("\n") + 1
    byte_count = len(output.encode("utf-8"))
    if line_count <= max_lines and byte_count <= max_bytes:
        return output, None
    spill_dir = _ensure_truncation_dir()
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    spill_path = spill_dir / f"tool_output_{ts}.txt"
    try:
        spill_path.write_text(output, encoding="utf-8")
    except OSError as e:
        logger.warning("Failed to write spill file %s: %s", spill_path, e)
        spill_path = None
    lines = output.splitlines()
    half = max_lines // 2
    head = lines[:half]
    tail = lines[-half:] if len(lines) > half else []
    truncated = "\n".join(head)
    if tail:
        truncated += f"\n[... {line_count - max_lines} lines truncated ...]\n"
        truncated += "\n".join(tail)
    truncated += (
        f"\n\n<output truncated — full output: {len(lines)} lines, "
        f"{byte_count:,} bytes>"
    )
    if spill_path:
        truncated += f"\nTo read full output: `read_file path=\"{spill_path}\"`"
    return truncated, str(spill_path) if spill_path else None


def extract_target(args: dict) -> Optional[str]:
    for key in ("target", "host", "domain", "url", "ip", "rhosts", "rhost", "hostnames", "target_url", "target_ip"):
        val = args.get(key)
        if val and isinstance(val, str) and val.strip():
            return val.strip()
    return None


def validate_option_key(key: str) -> bool:
    return bool(_SAFE_KEY_RE.match(key))


def validate_option_value(value: str) -> bool:
    return not _DANGEROUS_VALUE_RE.search(value)


def run_command(cmd: str, timeout: int = 300, **kwargs) -> subprocess.CompletedProcess:
    return subprocess.run(
        cmd,
        shell=True,
        capture_output=True,
        text=True,
        timeout=timeout,
        **kwargs,
    )


def run_command_argv(
    argv: list[str],
    timeout: int = 300,
    **kwargs,
) -> subprocess.CompletedProcess:
    return subprocess.run(
        argv,
        shell=False,
        capture_output=True,
        text=True,
        timeout=timeout,
        **kwargs,
    )


def json_result(success: bool, data: any = None, error: str = None) -> str:
    result = {"success": success}
    if data is not None:
        result["data"] = data
    if error is not None:
        result["error"] = error
    return json.dumps(result, indent=2)


def tool_error(message: str) -> str:
    return json_result(False, error=message)
