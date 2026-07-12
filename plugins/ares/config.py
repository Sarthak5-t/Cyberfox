from __future__ import annotations

import logging
import os
import re
import time
from ipaddress import ip_address, ip_network
from pathlib import Path

logger = logging.getLogger(__name__)

_CONFIG_CACHE = None
_CONFIG_MTIME = 0.0


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
        self.safety_scope_enforcement: str = "disabled"
        self.safety_doom_loop_threshold: int = 0
        self.safety_require_exploit_approval: bool = False
        self.safety_log_all_commands: bool = True
        self.scope_file: str = "scope.yaml"

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
                safety = ares_cfg.get("safety", {})
                self.safety_scope_enforcement = safety.get("scope_enforcement", "enforced")
                self.safety_doom_loop_threshold = safety.get("doom_loop_threshold", 5)
                self.safety_require_exploit_approval = safety.get("require_exploit_approval", False)
                self.safety_log_all_commands = safety.get("log_all_commands", True)
            except Exception as e:
                logger.warning("Failed to load Ares config: %s", e)

        scope_path = self.home / "profiles" / "ares" / self.scope_file
        if scope_path.exists():
            try:
                import yaml
                with open(scope_path) as f:
                    data = yaml.safe_load(f) or {}
                self.scope = data.get("scope", [])
            except Exception as e:
                logger.warning("Failed to load scope file: %s", e)

    def is_target_in_scope(self, target: str) -> bool:
        if not self.scope:
            return self.safety_scope_enforcement != "enforced"
        clean = target.split(":")[0].strip().rstrip("/")
        try:
            addr = ip_address(clean)
            for entry in self.scope:
                try:
                    if addr in ip_network(entry, strict=False):
                        return True
                except ValueError:
                    pass
            return False
        except ValueError:
            pass
        for entry in self.scope:
            entry_clean = entry.strip().lower()
            if clean.lower() == entry_clean:
                return True
            if clean.lower().endswith("." + entry_clean):
                return True
        return False

    target_in_scope = is_target_in_scope


def get_config(home: Path | None = None) -> AresConfig:
    global _CONFIG_CACHE, _CONFIG_MTIME
    config_path = (home or _resolve_home()) / "profiles" / "ares" / "config.yaml"
    try:
        mtime = config_path.stat().st_mtime if config_path.exists() else 0.0
    except OSError:
        mtime = 0.0
    if _CONFIG_CACHE is not None and mtime == _CONFIG_MTIME:
        return _CONFIG_CACHE
    cfg = AresConfig(home)
    cfg.load()
    _CONFIG_CACHE = cfg
    _CONFIG_MTIME = mtime
    return cfg


def reload_config() -> AresConfig:
    global _CONFIG_CACHE, _CONFIG_MTIME
    _CONFIG_CACHE = None
    _CONFIG_MTIME = 0.0
    return get_config()
