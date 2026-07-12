from __future__ import annotations

import logging

from plugins.ares.state import engagement_store as store

logger = logging.getLogger(__name__)

_MAX_CONTEXT_CHARS = 2000


def pre_llm_call(
    messages: list[dict] | None = None,
    session_id: str = None,
    **kwargs,
) -> str | None:
    """Inject knowledge graph summary into LLM context before each call."""
    if not messages:
        return None
    eng = store.get_engagement()
    if not eng:
        return None
    try:
        summary = store.get_context_summary(eng.id, max_chars=_MAX_CONTEXT_CHARS)
    except Exception:
        return None
    if not summary or len(summary) < 20:
        return None
    return (
        f"[ARES CONTEXT — Engagement '{eng.name}' (state: {eng.state})]\n"
        f"{summary}\n"
        f"[END ARES CONTEXT]"
    )
