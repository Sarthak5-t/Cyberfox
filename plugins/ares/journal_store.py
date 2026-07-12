from __future__ import annotations

import datetime
import threading
from pathlib import Path
from typing import Optional

from cyberfox_constants import get_cyberfox_home as get_cf_home

_LOCK = threading.Lock()

_JOURNAL_DIR = "ares"
_JOURNAL_FILE = "journal.md"
_MAX_JOURNAL_CHARS = 8000


def _journal_path() -> Path:
    return get_cf_home() / _JOURNAL_DIR / _JOURNAL_FILE


def _ensure_dir() -> None:
    _journal_path().parent.mkdir(parents=True, exist_ok=True)


def _timestamp() -> str:
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M")


def init_journal(engagement_name: str = "engagement", targets: str = "") -> None:
    _ensure_dir()
    now = _timestamp()
    header = f"# Engagement Journal\n\n"
    header += f"**Engagement:** {engagement_name}\n"
    header += f"**Started:** {now}\n"
    if targets:
        header += f"**Targets:** {targets}\n"
    header += f"\n---\n\n"
    with _LOCK:
        _journal_path().write_text(header, encoding="utf-8")


def append_entry(
    category: str,
    content: str,
    target: Optional[str] = None,
) -> bool:
    _ensure_dir()
    now = _timestamp()
    target_tag = f" [{target}]" if target else ""
    entry = f"### [{now}]{target_tag} {category.title()}\n{content.strip()}\n\n"

    with _LOCK:
        try:
            existing = ""
            p = _journal_path()
            if p.exists():
                existing = p.read_text(encoding="utf-8")
            # Prepend new entry after header (after first ---)
            parts = existing.split("---\n\n", 1)
            if len(parts) == 2:
                header, body = parts
                # Truncate body if too long
                if len(body) > _MAX_JOURNAL_CHARS:
                    lines = body.split("\n")
                    half = len(lines) // 2
                    body = "\n".join(lines[:half]) + "\n\n[... older entries truncated ...]\n\n" + "\n".join(lines[half:])
                new_content = f"{header}---\n\n{entry}{body}"
            else:
                new_content = f"{existing}\n{entry}"
            p.write_text(new_content, encoding="utf-8")
            return True
        except OSError:
            return False


def read_journal() -> str:
    p = _journal_path()
    if not p.exists():
        return ""
    with _LOCK:
        return p.read_text(encoding="utf-8")


def read_recent(n: int = 20) -> str:
    full = read_journal()
    if not full:
        return ""
    # Split into entries (### markers)
    sections = full.split("### ")
    if len(sections) <= 1:
        return full
    header = sections[0]
    entries = ["### " + s for s in sections[1:]]
    recent = entries[-n:] if len(entries) > n else entries
    return header + "\n".join(recent)


def search_journal(query: str) -> str:
    full = read_journal()
    if not full or not query:
        return ""
    query_lower = query.lower()
    matches = []
    current_entry = ""
    for line in full.split("\n"):
        if line.startswith("### "):
            if current_entry and query_lower in current_entry.lower():
                matches.append(current_entry)
            current_entry = line + "\n"
        else:
            current_entry += line + "\n"
    if current_entry and query_lower in current_entry.lower():
        matches.append(current_entry)
    return "\n".join(matches) if matches else f"No entries matching '{query}' found."


def journal_exists() -> bool:
    return _journal_path().exists()
