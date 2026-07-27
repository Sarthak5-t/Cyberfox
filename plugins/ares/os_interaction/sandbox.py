from __future__ import annotations

import logging
import os
import shutil
import tempfile
import time
from dataclasses import dataclass, field
from typing import Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class SandboxConfig:
    """Configuration for a security sandbox."""
    sandbox_id: str
    base_directory: str
    allowed_commands: list[str]
    blocked_commands: list[str]
    max_file_size: int  # bytes
    max_execution_time: float  # seconds
    network_allowed: bool
    filesystem_allowed: bool
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class Sandbox:
    """A security sandbox for isolating tool execution."""
    config: SandboxConfig
    created_at: float
    is_active: bool
    working_directory: str
    environment: dict[str, str] = field(default_factory=dict)


class SecuritySandbox:
    """Security sandbox for isolating tool execution."""

    def __init__(self):
        self._sandboxes: dict[str, Sandbox] = {}
        self._sandbox_counter = 0
        self._temp_dir_base = tempfile.gettempdir()

    def create_sandbox(
        self,
        name: str,
        allowed_commands: Optional[list[str]] = None,
        blocked_commands: Optional[list[str]] = None,
        max_file_size: int = 10 * 1024 * 1024,  # 10MB
        max_execution_time: float = 300,  # 5 minutes
        network_allowed: bool = False,
        filesystem_allowed: bool = True,
        metadata: Optional[dict[str, Any]] = None,
    ) -> Sandbox:
        """Create a new security sandbox."""
        self._sandbox_counter += 1
        sandbox_id = f"sandbox_{self._sandbox_counter}"

        # Create isolated directory
        sandbox_dir = os.path.join(
            self._temp_dir_base,
            f"ares_sandbox_{sandbox_id}",
        )
        os.makedirs(sandbox_dir, exist_ok=True)

        # Create subdirectories
        os.makedirs(os.path.join(sandbox_dir, "work"), exist_ok=True)
        os.makedirs(os.path.join(sandbox_dir, "output"), exist_ok=True)
        os.makedirs(os.path.join(sandbox_dir, "temp"), exist_ok=True)

        config = SandboxConfig(
            sandbox_id=sandbox_id,
            base_directory=sandbox_dir,
            allowed_commands=allowed_commands or [],
            blocked_commands=blocked_commands or [
                "rm -rf /",
                "dd if=",
                "mkfs",
                ":(){:|:&};:",
            ],
            max_file_size=max_file_size,
            max_execution_time=max_execution_time,
            network_allowed=network_allowed,
            filesystem_allowed=filesystem_allowed,
            metadata=metadata or {},
        )

        sandbox = Sandbox(
            config=config,
            created_at=time.time(),
            is_active=True,
            working_directory=os.path.join(sandbox_dir, "work"),
            environment={
                "SANDBOX_ID": sandbox_id,
                "SANDBOX_DIR": sandbox_dir,
                "HOME": os.path.join(sandbox_dir, "work"),
                "TMPDIR": os.path.join(sandbox_dir, "temp"),
            },
        )

        self._sandboxes[sandbox_id] = sandbox
        logger.info(f"Sandbox created: {sandbox_id} at {sandbox_dir}")
        return sandbox

    def destroy_sandbox(self, sandbox_id: str) -> bool:
        """Destroy a sandbox and clean up resources."""
        if sandbox_id not in self._sandboxes:
            return False

        sandbox = self._sandboxes[sandbox_id]
        sandbox.is_active = False

        # Remove sandbox directory
        try:
            if os.path.exists(sandbox.config.base_directory):
                shutil.rmtree(sandbox.config.base_directory)
            logger.info(f"Sandbox destroyed: {sandbox_id}")
        except Exception as e:
            logger.error(f"Failed to destroy sandbox {sandbox_id}: {e}")
            return False

        del self._sandboxes[sandbox_id]
        return True

    def validate_command(
        self,
        sandbox_id: str,
        command: str,
    ) -> tuple[bool, str]:
        """Validate if a command is allowed in the sandbox."""
        if sandbox_id not in self._sandboxes:
            return False, "Sandbox not found"

        sandbox = self._sandboxes[sandbox_id]
        if not sandbox.is_active:
            return False, "Sandbox is not active"

        # Check blocked commands
        for blocked in sandbox.config.blocked_commands:
            if blocked in command:
                return False, f"Command contains blocked pattern: {blocked}"

        # Check allowed commands (if specified)
        if sandbox.config.allowed_commands:
            command_base = command.split()[0] if command else ""
            if command_base not in sandbox.config.allowed_commands:
                return False, f"Command not in allowed list: {command_base}"

        # Check network commands if network not allowed
        if not sandbox.config.network_allowed:
            network_commands = [
                "curl", "wget", "nc", "netcat", "ssh", "scp", "rsync",
                "nmap", "masscan", "hydra", "medusa",
            ]
            command_base = command.split()[0] if command else ""
            if command_base in network_commands:
                return False, f"Network command not allowed in sandbox: {command_base}"

        return True, "Command is allowed"

    def get_sandbox(self, sandbox_id: str) -> Optional[Sandbox]:
        """Get a sandbox by ID."""
        return self._sandboxes.get(sandbox_id)

    def list_sandboxes(self) -> list[Sandbox]:
        """List all active sandboxes."""
        return list(self._sandboxes.values())

    def get_sandbox_environment(self, sandbox_id: str) -> dict[str, str]:
        """Get the environment variables for a sandbox."""
        if sandbox_id not in self._sandboxes:
            return {}
        return self._sandboxes[sandbox_id].environment.copy()

    def check_file_size(
        self,
        sandbox_id: str,
        file_path: str,
    ) -> bool:
        """Check if a file size is within sandbox limits."""
        if sandbox_id not in self._sandboxes:
            return False

        sandbox = self._sandboxes[sandbox_id]

        try:
            file_size = os.path.getsize(file_path)
            return file_size <= sandbox.config.max_file_size
        except OSError:
            return False

    def get_statistics(self) -> dict[str, Any]:
        """Get sandbox statistics."""
        return {
            "total_sandboxes": len(self._sandboxes),
            "active_sandboxes": sum(1 for s in self._sandboxes.values() if s.is_active),
        }


# Global instance
_security_sandbox: Optional[SecuritySandbox] = None


def get_security_sandbox() -> SecuritySandbox:
    """Get the global security sandbox instance."""
    global _security_sandbox
    if _security_sandbox is None:
        _security_sandbox = SecuritySandbox()
    return _security_sandbox
