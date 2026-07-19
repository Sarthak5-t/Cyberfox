"""Tokenjuice — rule-based token compressor for Ares tool outputs.

Inspired by OpenHuman's tokenjuice module.  Provides content-aware
compression that detects output kind (JSON, code, HTML, XML, log, plain)
and applies the appropriate compressor rules to shrink token usage before
results are handed back to the LLM.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Optional

from plugins.ares.tools.base import truncate_output

logger = logging.getLogger(__name__)

__all__ = [
    "compress",
    "compress_then_truncate",
    "detect_kind",
    "estimate_tokens",
]

# ── kind detection ──────────────────────────────────────────────────

_JSON_LEADERS = frozenset("{[")
_HTML_RE = re.compile(
    r"<!DOCTYPE\b|<html\b|<head\b|<body\b|<div\b|<span\b|<p\b|<table\b|<a\b[\s>]",
    re.IGNORECASE,
)
_XML_RE = re.compile(r"<\?xml\b|<[a-zA-Z:]+[\s>/]", re.DOTALL)
_CODE_INDENT_RE = re.compile(r"^(?:    |\t)", re.MULTILINE)
_LOG_TS_RE = re.compile(
    r"^\d{4}[-/]\d{2}[-/]\d{2}|^\d{2}:\d{2}:\d{2}|\[[\w.:-]+\]"
)
_LOG_PATTERNS = re.compile(
    r"^(?:ERROR|WARNING|INFO|DEBUG|FATAL|CRITICAL|NOTICE)\b|"
    r"^\d+/tcp\s+open|"
    r"^\[[\w!.-]+\]\s|"
    r"^\*\*\s|"
    r"^\[CVE-\d{4}-\d+\]|"
    r"^Status:\s|"
    r"^PORT\s|"
    r"^Starting\s|"
    r"^Nmap\s"
)


def detect_kind(text: str) -> str:
    """Return one of ``json``, ``code``, ``html``, ``xml``, ``log`` or ``plain``."""
    if not text or not text.strip():
        return "plain"

    stripped = text.lstrip()
    first_char = stripped[0] if stripped else ""

    # ── JSON ──
    if first_char in _JSON_LEADERS:
        try:
            json.loads(stripped)
            return "json"
        except (json.JSONDecodeError, ValueError):
            pass

    # ── HTML / XML ──
    if first_char == "<":
        if _HTML_RE.search(stripped[:512]):
            return "html"
        if _XML_RE.search(stripped[:512]):
            return "xml"

    # ── Log ──
    sample_lines = stripped.splitlines()[:20]
    if sample_lines:
        ts_hits = sum(
            1 for ln in sample_lines
            if _LOG_TS_RE.match(ln) or _LOG_PATTERNS.match(ln)
        )
        if ts_hits / len(sample_lines) >= 0.3:
            return "log"

    # ── Code ──
    if _CODE_INDENT_RE.search(stripped):
        return "code"

    return "plain"


# ── helpers ─────────────────────────────────────────────────────────


def estimate_tokens(text: str) -> int:
    """Rough token estimate: ~4 characters per token."""
    return max(1, len(text) // 4)


# ── compressor rules ───────────────────────────────────────────────

def _json_shrink(text: str) -> str:
    """Strip whitespace, remove redundant keys, collapse short arrays."""
    try:
        parsed = json.loads(text)
    except (json.JSONDecodeError, ValueError):
        return text
    cleaned = _json_strip_redundant(parsed)
    return json.dumps(cleaned, separators=(",", ":"), ensure_ascii=False)


def _json_strip_redundant(obj: object) -> object:
    """Recursively remove known-empty / null values and collapse arrays."""
    if isinstance(obj, dict):
        out = {}
        for k, v in obj.items():
            if v is None or v == "" or v == [] or v == {}:
                continue
            out[k] = _json_strip_redundant(v)
        return out
    if isinstance(obj, list):
        if len(obj) <= 8:
            return [_json_strip_redundant(i) for i in obj]
        return [_json_strip_redundant(i) for i in obj[:4]] + [f"... +{len(obj) - 4} more"]
    return obj


def _code_dedent(text: str) -> str:
    """Remove leading blank lines and strip the common leading indentation."""
    lines = text.splitlines()
    if not lines:
        return text

    # strip leading blank lines
    while lines and not lines[0].strip():
        lines.pop(0)
    while lines and not lines[-1].strip():
        lines.pop()

    if not lines:
        return text

    # find minimum indentation (ignoring blank lines)
    indents = []
    for line in lines:
        if line.strip():
            indents.append(len(line) - len(line.lstrip()))
    if not indents:
        return text

    common = min(indents)
    if common == 0:
        return "\n".join(lines)
    return "\n".join(line[common:] if line.strip() else "" for line in lines)


def _html_extract(text: str) -> str:
    """Strip tags, keep text content, collapse whitespace."""
    clean = re.sub(r"<script[^>]*>.*?</script>", "", text, flags=re.DOTALL | re.IGNORECASE)
    clean = re.sub(r"<style[^>]*>.*?</style>", "", clean, flags=re.DOTALL | re.IGNORECASE)
    clean = re.sub(r"<[^>]+>", " ", clean)
    clean = re.sub(r"&nbsp;", " ", clean)
    clean = re.sub(r"&[a-zA-Z]+;", " ", clean)
    clean = re.sub(r"[ \t]+", " ", clean)
    clean = re.sub(r"\n{3,}", "\n\n", clean)
    return clean.strip()


def _xml_collapse(text: str) -> str:
    """Collapse self-closing tags, remove empty elements, strip comments."""
    text = re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)
    text = re.sub(r"<(\w+)[^/]*/>", r"<\1/>", text)
    text = re.sub(r"<(\w+)>\s*</\1>", "", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _log_dedup(text: str) -> str:
    """Collapse consecutive identical lines into a count summary."""
    lines = text.splitlines()
    if not lines:
        return text

    out: list[str] = []
    run_start = 0
    i = 1
    while i <= len(lines):
        if i < len(lines) and lines[i] == lines[run_start]:
            i += 1
            continue
        count = i - run_start
        if count >= 3:
            out.append(f"[{lines[run_start]}] x{count}")
        else:
            out.extend(lines[run_start:i])
        run_start = i
        i += 1

    return "\n".join(out)


# registry ───────────────────────────────────────────────────────────

_RULES: dict[str, tuple[str, callable]] = {
    "json": ("json_shrink", _json_shrink),
    "code": ("code_dedent", _code_dedent),
    "html": ("html_extract", _html_extract),
    "xml": ("xml_collapse", _xml_collapse),
    "log": ("log_dedup", _log_dedup),
}


# ── main API ────────────────────────────────────────────────────────

def compress(
    output: str,
    kind: str | None = None,
    budget: int | None = None,
) -> tuple[str, dict]:
    """Compress *output* and return ``(compressed_text, stats)``.

    Parameters
    ----------
    output:
        Raw tool output to compress.
    kind:
        Output kind (``json``, ``code``, ``html``, ``xml``, ``log``,
        ``plain``).  When *None* the kind is auto-detected.
    budget:
        Target maximum character count.  If set, compressors are applied
        iteratively until the output is under budget or no further
        reduction is possible.

    Returns
    -------
    tuple[str, dict]
        The compressed text and a stats dict with keys
        ``original_bytes``, ``compressed_bytes``, ``ratio``, ``kind``,
        and ``rules_applied``.
    """
    if not output:
        return output, _stats("", output, kind or "plain", [])

    original_bytes = len(output.encode("utf-8"))

    if kind is None:
        kind = detect_kind(output)

    rules_applied: list[str] = []
    result = output

    rule_name, rule_fn = _RULES.get(kind, (None, None))
    if rule_fn is not None:
        compressed = rule_fn(result)
        if len(compressed) < len(result):
            result = compressed
            rules_applied.append(rule_name)

    # budget iteration — apply all available rules until under budget
    if budget is not None:
        rounds = 0
        while len(result) > budget and rounds < 6:
            before = result
            for rname, rfn in _RULES.values():
                if rname in rules_applied and rname != rule_name:
                    continue
                candidate = rfn(result)
                if len(candidate) < len(result):
                    result = candidate
                    if rname not in rules_applied:
                        rules_applied.append(rname)
            rounds += 1
            if result == before:
                break

    return result, _stats(result, output, kind, rules_applied)


def _stats(
    compressed: str,
    original: str,
    kind: str,
    rules_applied: list[str],
) -> dict:
    """Build the stats dictionary."""
    comp_bytes = len(compressed.encode("utf-8"))
    orig_bytes = len(original.encode("utf-8"))
    ratio = round(comp_bytes / orig_bytes, 3) if orig_bytes else 1.0
    return {
        "original_bytes": orig_bytes,
        "compressed_bytes": comp_bytes,
        "ratio": ratio,
        "kind": kind,
        "rules_applied": rules_applied,
    }


# ── integration with base.truncate_output ───────────────────────────


def compress_then_truncate(
    output: str,
    max_lines: int = 2000,
    max_bytes: int = 51200,
    kind: str | None = None,
    budget: int | None = None,
) -> tuple[str, Optional[str], dict]:
    """Compress first, then truncate if still too large.

    Parameters
    ----------
    output:
        Raw tool output.
    max_lines / max_bytes:
        Passed to :func:`truncate_output`.
    kind:
        Optional override for output kind detection.
    budget:
        Optional character budget passed to :func:`compress`.

    Returns
    -------
    tuple[str, str | None, dict]
        ``(compressed_text, spill_path_or_None, stats)``.
    """
    compressed, stats = compress(output, kind=kind, budget=budget)
    truncated, spill_path = truncate_output(compressed, max_lines=max_lines, max_bytes=max_bytes)
    return truncated, spill_path, stats
