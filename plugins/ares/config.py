from __future__ import annotations

import json
import logging
import os
from ipaddress import ip_address, ip_network, IPv4Network
from pathlib import Path

logger = logging.getLogger(__name__)

_CONFIG_CACHE = None


def _resolve_home() -> Path:
    env_home = os.getenv("CYBERFOX_HOME")
    if env_home:
        return Path(env_home)
    return Path.home() / ".cyberfox"


class AresConfig:
    def __init__(self, home: Path | None = None):
        self.home = home or _resolve_home()
        self.ares_enabled: bool = True
        self.requires_approval: list[str] | None = None
        self.max_chain_depth: int = 3
        self.audit_enabled: bool = True
        self.scope: list[str] = []
        self.auto_proceed: bool = False

    def load(self) -> None:
        config_path = self.home / "profiles" / "ares" / "config.yaml"
        if config_path.exists():
            try:
                import yaml
                with open(config_path) as f:
                    data = yaml.safe_load(f) or {}
                ares_cfg = data.get("ares", {})
                self.ares_enabled = ares_cfg.get("enabled", True)
                self.requires_approval = ares_cfg.get("requires_approval")
                self.max_chain_depth = ares_cfg.get("max_chain_depth", 3)
                self.audit_enabled = ares_cfg.get("audit_enabled", True)
                self.auto_proceed = ares_cfg.get("auto_proceed", False)
            except Exception as e:
                logger.warning("Failed to load Ares config: %s", e)

        scope_path = self.home / "profiles" / "ares" / "scope.yaml"
        if scope_path.exists():
            try:
                import yaml
                with open(scope_path) as f:
                    data = yaml.safe_load(f) or {}
                self.scope = data.get("scope", [])
            except Exception as e:
                logger.warning("Failed to load scope file: %s", e)

    def target_in_scope(self, target: str) -> bool:
        if not self.scope:
            return True
        try:
            addr = ip_address(target)
        except ValueError:
            try:
                addr = ip_address(target.split(":")[0])
            except ValueError:
                return True
        for entry in self.scope:
            try:
                network = ip_network(entry, strict=False)
                if addr in network:
                    return True
            except ValueError:
                pass
        return False


def get_config(home: Path | None = None) -> AresConfig:
    global _CONFIG_CACHE
    if _CONFIG_CACHE is None:
        cfg = AresConfig(home)
        cfg.load()
        _CONFIG_CACHE = cfg
    return _CONFIG_CACHE


def reload_config() -> AresConfig:
    global _CONFIG_CACHE
    _CONFIG_CACHE = None
    return get_config()
