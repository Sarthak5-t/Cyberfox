from __future__ import annotations

import fnmatch
import ipaddress
import logging
import re
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)


class ScopeError(Exception):
    """Raised when a target is out of scope."""
    pass


class ScopeEnforcer:
    """Hard scope boundary — rejects any target not explicitly in scope."""

    def __init__(self):
        self._in_scope: list[str] = []
        self._out_of_scope: list[str] = []
        self._scope_type: str = "permissive"  # permissive | enforced
        self._program_name: str = ""
        self._stats = {"allowed": 0, "blocked": 0}

    def load_from_file(self, filepath: str) -> None:
        """Load scope from YAML or plain text file."""
        path = Path(filepath)
        if not path.exists():
            logger.warning(f"Scope file not found: {filepath}")
            return

        try:
            import yaml
            with open(path) as f:
                data = yaml.safe_load(f) or {}
        except ImportError:
            data = self._parse_plaintext(path.read_text())

        if isinstance(data, dict):
            self._program_name = data.get("program", "")
            self._scope_type = data.get("type", "enforced")
            self._in_scope = [str(s) for s in data.get("in_scope", data.get("scope", []))]
            self._out_of_scope = [str(s) for s in data.get("out_of_scope", [])]
        elif isinstance(data, list):
            self._in_scope = data

        logger.info(f"Scope loaded: {len(self._in_scope)} in-scope, "
                    f"{len(self._out_of_scope)} excluded, program={self._program_name}")

    def load_from_program(self, program_data: dict) -> None:
        """Load scope from a bug bounty program dict (e.g. HackerOne API response)."""
        self._program_name = program_data.get("name", program_data.get("handle", ""))
        self._scope_type = "enforced"

        for asset in program_data.get("structured_scope", []):
            asset_type = asset.get("asset_type", "")
            identifier = asset.get("asset_identifier", "")
            instruction = asset.get("instruction", "")
            eligible = asset.get("eligible_for_bounty", True)

            if asset_type == "URL":
                if identifier.startswith("*."):
                    self._in_scope.append(identifier)
                else:
                    self._in_scope.append(identifier)
            elif asset_type == "CIDR":
                self._in_scope.append(identifier)
            elif asset_type == "WILDCARD":
                self._in_scope.append(identifier)

            if not eligible or "out of scope" in instruction.lower():
                self._out_of_scope.append(identifier)

    def _parse_plaintext(self, text: str) -> dict:
        lines = [l.strip() for l in text.strip().split("\n") if l.strip() and not l.startswith("#")]
        return {"in_scope": lines, "type": "enforced"}

    def set_scope(self, in_scope: list[str], out_of_scope: Optional[list[str]] = None) -> None:
        self._in_scope = in_scope
        self._out_of_scope = out_of_scope or []

    def is_in_scope(self, target: str) -> bool:
        """Check if a target is in scope. Supports wildcards, CIDR, domains, URLs."""
        target_clean = target.strip().lower()
        # Extract host from URL
        target_clean = re.sub(r'^https?://', '', target_clean)
        target_clean = target_clean.split('/')[0].split(':')[0].strip()

        # Check out-of-scope first
        for exclusion in self._out_of_scope:
            if self._match_entry(target_clean, exclusion):
                return False

        # Check in-scope
        for entry in self._in_scope:
            if self._match_entry(target_clean, entry):
                return True

        return False

    def _match_entry(self, target: str, entry: str) -> bool:
        entry_clean = entry.strip().lower()

        # CIDR match
        try:
            net = ipaddress.ip_network(entry_clean, strict=False)
            try:
                addr = ipaddress.ip_address(target)
                return addr in net
            except ValueError:
                pass
        except ValueError:
            pass

        # Wildcard/fnmatch
        if entry_clean.startswith('*.'):
            base = entry_clean[2:]
            if target == base or target.endswith('.' + base):
                return True
            return fnmatch.fnmatch(target, entry_clean)

        # fnmatch pattern
        if '*' in entry_clean or '?' in entry_clean:
            return fnmatch.fnmatch(target, entry_clean)

        # Exact match
        return target == entry_clean

    def enforce(self, target: str) -> None:
        """Raise ScopeError if target is not in scope."""
        self._stats["allowed"] += 1
        if not self._in_scope:
            if self._scope_type == "permissive":
                return
            self._stats["blocked"] += 1
            raise ScopeError(
                f"NO SCOPE DEFINED. Target '{target}' blocked. "
                f"Define scope in scope.yaml or program config."
            )

        if not self.is_in_scope(target):
            self._stats["blocked"] += 1
            raise ScopeError(
                f"Target '{target}' is OUT OF SCOPE. "
                f"In-scope: {self._in_scope[:5]}{'...' if len(self._in_scope) > 5 else ''}"
            )

    def get_stats(self) -> dict[str, Any]:
        return {
            "program": self._program_name,
            "scope_type": self._scope_type,
            "in_scope_count": len(self._in_scope),
            "exclusions_count": len(self._out_of_scope),
            "allowed": self._stats["allowed"],
            "blocked": self._stats["blocked"],
        }


_scope_enforcer: Optional[ScopeEnforcer] = None


def get_scope_enforcer() -> ScopeEnforcer:
    global _scope_enforcer
    if _scope_enforcer is None:
        _scope_enforcer = ScopeEnforcer()
    return _scope_enforcer
