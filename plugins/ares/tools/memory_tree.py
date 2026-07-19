from __future__ import annotations

import json
import logging
import os
import re
import time
import uuid
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

_STORAGE_DIR = Path(os.path.expanduser("~/.cyberfox/ares"))
_STORAGE_FILE = _STORAGE_DIR / "memory_tree.json"

_APPROX_CHARS_PER_TOKEN = 4


@dataclass
class MemoryNode:
    node_id: str
    content: str
    node_type: str  # "root" | "branch" | "leaf"
    children: list[MemoryNode] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)
    depth: int = 0

    # ── helpers ──────────────────────────────────────────────────────

    def token_estimate(self) -> int:
        return len(self.content) // _APPROX_CHARS_PER_TOKEN

    def child_count(self) -> int:
        return len(self.children)


class MemoryTree:

    def __init__(
        self,
        max_leaf_tokens: int = 500,
        max_depth: int = 4,
    ) -> None:
        self.max_leaf_tokens = max_leaf_tokens
        self.max_depth = max_depth
        self.root: MemoryNode = self._make_root()
        self._index: dict[str, MemoryNode] = {self.root.node_id: self.root}

    # ── construction ─────────────────────────────────────────────────

    @staticmethod
    def _generate_id() -> str:
        return uuid.uuid4().hex[:12]

    @staticmethod
    def _make_root() -> MemoryNode:
        return MemoryNode(
            node_id=MemoryTree._generate_id(),
            content="memory_tree_root",
            node_type="root",
            metadata={"tool_name": "", "timestamp": time.time()},
            depth=0,
        )

    def _index_node(self, node: MemoryNode) -> None:
        self._index[node.node_id] = node

    def _rebuild_index(self) -> None:
        self._index.clear()
        self._walk(self.root)

    def _walk(self, node: MemoryNode) -> None:
        self._index[node.node_id] = node
        for child in node.children:
            self._walk(child)

    # ── splitting ────────────────────────────────────────────────────

    @staticmethod
    def _split_content(content: str, max_tokens: int) -> list[str]:
        max_chars = max_tokens * _APPROX_CHARS_PER_TOKEN
        if len(content) <= max_chars:
            return [content]

        chunks: list[str] = []
        remaining = content

        while remaining:
            if len(remaining) <= max_chars:
                chunks.append(remaining)
                break

            window = remaining[:max_chars]

            split_at = -1
            for sep in ("\n\n", "\n", ". ", ".\n", "; ", ", ", " "):
                idx = window.rfind(sep)
                if idx > max_chars // 3:
                    split_at = idx + len(sep)
                    break

            if split_at == -1:
                split_at = max_chars

            chunks.append(remaining[:split_at].rstrip())
            remaining = remaining[split_at:].lstrip()

        return [c for c in chunks if c.strip()]

    # ── ingest ───────────────────────────────────────────────────────

    def ingest(
        self,
        content: str,
        source: str = "",
        tool_name: str = "",
    ) -> MemoryNode:
        content = content.strip()
        if not content:
            content = "(empty output)"

        tokens_est = len(content) // _APPROX_CHARS_PER_TOKEN

        if tokens_est <= self.max_leaf_tokens:
            node = self._make_leaf(content, source, tool_name)
            self.root.children.append(node)
            self._index_node(node)
            logger.debug("Ingested leaf %s (%d tokens)", node.node_id, tokens_est)
            return node

        chunks = self._split_content(content, self.max_leaf_tokens)
        branch = MemoryNode(
            node_id=self._generate_id(),
            content=chunks[0][:200] + ("…" if len(chunks[0]) > 200 else ""),
            node_type="branch",
            metadata={
                "tool_name": tool_name,
                "source": source,
                "timestamp": time.time(),
                "token_estimate": tokens_est,
                "compression_ratio": 1.0,
                "chunk_count": len(chunks),
            },
            depth=self.root.depth + 1,
        )
        self._index_node(branch)

        for chunk in chunks:
            child = self._make_leaf(chunk, source, tool_name, depth=branch.depth + 1)
            branch.children.append(child)
            self._index_node(child)

        branch.metadata["compression_ratio"] = (
            self._leaf_tokens(branch) / tokens_est if tokens_est else 1.0
        )

        self.root.children.append(branch)
        logger.debug(
            "Ingested branch %s (%d chunks, ~%d tokens)",
            branch.node_id,
            len(chunks),
            tokens_est,
        )
        return branch

    def _make_leaf(
        self,
        content: str,
        source: str,
        tool_name: str,
        depth: int = 1,
    ) -> MemoryNode:
        tokens = len(content) // _APPROX_CHARS_PER_TOKEN
        return MemoryNode(
            node_id=self._generate_id(),
            content=content,
            node_type="leaf",
            metadata={
                "tool_name": tool_name,
                "source": source,
                "timestamp": time.time(),
                "token_estimate": tokens,
            },
            depth=depth,
        )

    # ── summarize ────────────────────────────────────────────────────

    def summarize(
        self,
        node_id: str | None = None,
        depth: int = 2,
    ) -> str:
        target = self._resolve(node_id, self.root)
        return self._render(target, depth, 0)

    def _render(self, node: MemoryNode, max_depth: int, current: int) -> str:
        indent = "  " * current
        prefix_map = {"root": "◆", "branch": "▸", "leaf": "•"}
        prefix = prefix_map.get(node.node_type, "•")

        token_est = node.metadata.get("token_estimate", node.token_estimate())
        header = f"{indent}{prefix} [{node.node_type}] {node.content[:80]}"
        if node.node_type == "branch":
            header += f" ({node.child_count()} children, ~{token_est} tokens)"
        elif node.node_type == "leaf":
            header += f" (~{token_est} tokens)"

        lines = [header]

        if current < max_depth and node.children:
            for child in node.children:
                lines.append(self._render(child, max_depth, current + 1))
        elif node.children:
            lines.append(f"{indent}  … {len(node.children)} more nodes (depth limit)")

        return "\n".join(lines)

    # ── search ───────────────────────────────────────────────────────

    def search(
        self,
        query: str,
        node_id: str | None = None,
    ) -> list[MemoryNode]:
        query_lower = query.lower()
        target = self._resolve(node_id, self.root)
        hits: list[MemoryNode] = []
        self._search_walk(target, query_lower, hits)
        return hits

    def _search_walk(
        self,
        node: MemoryNode,
        query_lower: str,
        hits: list[MemoryNode],
    ) -> None:
        if query_lower in node.content.lower():
            hits.append(node)
        if query_lower in str(node.metadata).lower():
            if node not in hits:
                hits.append(node)
        for child in node.children:
            self._search_walk(child, query_lower, hits)

    # ── prune ────────────────────────────────────────────────────────

    def prune(self, max_age_hours: int = 24) -> int:
        cutoff = time.time() - (max_age_hours * 3600)
        removed = 0
        for child in list(self.root.children):
            removed += self._prune_walk(child, cutoff, self.root)
        self._rebuild_index()
        return removed

    def _prune_walk(
        self,
        node: MemoryNode,
        cutoff: float,
        parent: MemoryNode,
    ) -> int:
        ts = node.metadata.get("timestamp", 0)
        removed = 0

        for child in list(node.children):
            removed += self._prune_walk(child, cutoff, node)

        if ts < cutoff and node.node_type != "root":
            parent.children.remove(node)
            removed += 1

        return removed

    # ── flatten ──────────────────────────────────────────────────────

    def flatten(self, node_id: str | None = None) -> list[MemoryNode]:
        target = self._resolve(node_id, self.root)
        nodes: list[MemoryNode] = []
        self._flatten_walk(target, nodes)
        return nodes

    def _flatten_walk(self, node: MemoryNode, out: list[MemoryNode]) -> None:
        out.append(node)
        for child in node.children:
            self._flatten_walk(child, out)

    # ── token count ──────────────────────────────────────────────────

    def token_estimate(self, node_id: str | None = None) -> int:
        target = self._resolve(node_id, self.root)
        return self._leaf_tokens(target)

    def _leaf_tokens(self, node: MemoryNode) -> int:
        if node.node_type == "leaf":
            return node.token_estimate()
        total = 0
        for child in node.children:
            total += self._leaf_tokens(child)
        return total

    # ── serialization ────────────────────────────────────────────────

    def to_dict(self, node: MemoryNode | None = None) -> dict:
        target = node or self.root
        return {
            "node_id": target.node_id,
            "content": target.content,
            "node_type": target.node_type,
            "metadata": target.metadata,
            "depth": target.depth,
            "children": [self.to_dict(c) for c in target.children],
            "max_leaf_tokens": self.max_leaf_tokens,
            "max_depth": self.max_depth,
        }

    @classmethod
    def from_dict(cls, data: dict) -> MemoryTree:
        tree = cls(
            max_leaf_tokens=data.get("max_leaf_tokens", 500),
            max_depth=data.get("max_depth", 4),
        )
        tree.root = cls._node_from_dict(data, depth=0)
        tree._rebuild_index()
        return tree

    @classmethod
    def _node_from_dict(cls, data: dict, depth: int) -> MemoryNode:
        children = [
            cls._node_from_dict(c, depth + 1) for c in data.get("children", [])
        ]
        return MemoryNode(
            node_id=data.get("node_id", cls._generate_id()),
            content=data.get("content", ""),
            node_type=data.get("node_type", "leaf"),
            children=children,
            metadata=data.get("metadata", {}),
            depth=depth,
        )

    # ── persistence ──────────────────────────────────────────────────

    def save(self, path: str | Path | None = None) -> None:
        path = Path(path) if path else _STORAGE_FILE
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        try:
            tmp.write_text(json.dumps(self.to_dict(), indent=2), encoding="utf-8")
            tmp.replace(path)
            logger.debug("MemoryTree saved to %s", path)
        except Exception:
            tmp.unlink(missing_ok=True)
            raise

    @classmethod
    def load(cls, path: str | Path | None = None) -> MemoryTree:
        path = Path(path) if path else _STORAGE_FILE
        if not path.exists():
            logger.info("No memory tree at %s, returning empty tree", path)
            return cls()
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            tree = cls.from_dict(data)
            logger.debug("MemoryTree loaded from %s", path)
            return tree
        except (json.JSONDecodeError, KeyError):
            logger.warning("Corrupt memory tree at %s, returning empty tree", path)
            return cls()

    # ── internal ─────────────────────────────────────────────────────

    def _resolve(self, node_id: str | None, default: MemoryNode) -> MemoryNode:
        if node_id is None:
            return default
        return self._index.get(node_id, default)


# ── module-level convenience ──────────────────────────────────────────

ARES_MEMORY = MemoryTree()


def ingest_output(
    content: str,
    source: str = "",
    tool_name: str = "",
) -> MemoryNode:
    node = ARES_MEMORY.ingest(content, source=source, tool_name=tool_name)
    try:
        ARES_MEMORY.save()
    except Exception as exc:
        logger.warning("Failed to persist memory tree: %s", exc)
    return node
