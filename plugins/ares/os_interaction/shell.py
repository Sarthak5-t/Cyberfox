from __future__ import annotations

import logging
import os
import shlex
import subprocess
import time
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class CommandResult:
    """Result of a shell command execution."""
    command: str
    return_code: int
    stdout: str
    stderr: str
    execution_time: float
    success: bool
    metadata: dict[str, Any] = field(default_factory=dict)


class EnhancedShell:
    """Enhanced shell execution with output parsing and command chaining."""

    def __init__(self):
        self._command_history: list[CommandResult] = []
        self._working_directory = os.getcwd()
        self._environment = os.environ.copy()
        self._command_counter = 0

    def execute(
        self,
        command: str,
        cwd: Optional[str] = None,
        env: Optional[dict[str, str]] = None,
        timeout: Optional[float] = None,
        capture_output: bool = True,
    ) -> CommandResult:
        """Execute a shell command."""
        start_time = time.time()
        self._command_counter += 1

        # Prepare environment
        exec_env = self._environment.copy()
        if env:
            exec_env.update(env)

        # Use specified cwd or default
        exec_cwd = cwd or self._working_directory

        try:
            result = subprocess.run(
                command,
                shell=True,
                cwd=exec_cwd,
                env=exec_env,
                capture_output=capture_output,
                text=True,
                timeout=timeout,
            )

            execution_time = time.time() - start_time
            command_result = CommandResult(
                command=command,
                return_code=result.returncode,
                stdout=result.stdout if capture_output else "",
                stderr=result.stderr if capture_output else "",
                execution_time=execution_time,
                success=result.returncode == 0,
                metadata={
                    "cwd": exec_cwd,
                    "timeout": timeout,
                },
            )

            self._command_history.append(command_result)
            logger.info(f"Command executed: {command} (exit code: {result.returncode})")
            return command_result

        except subprocess.TimeoutExpired:
            execution_time = time.time() - start_time
            command_result = CommandResult(
                command=command,
                return_code=-1,
                stdout="",
                stderr=f"Command timed out after {timeout} seconds",
                execution_time=execution_time,
                success=False,
                metadata={"timeout_exceeded": True},
            )
            self._command_history.append(command_result)
            logger.warning(f"Command timed out: {command}")
            return command_result

        except Exception as e:
            execution_time = time.time() - start_time
            command_result = CommandResult(
                command=command,
                return_code=-1,
                stdout="",
                stderr=str(e),
                execution_time=execution_time,
                success=False,
                metadata={"exception": str(e)},
            )
            self._command_history.append(command_result)
            logger.error(f"Command failed: {command} - {e}")
            return command_result

    def execute_chain(
        self,
        commands: list[str],
        stop_on_failure: bool = True,
        cwd: Optional[str] = None,
        env: Optional[dict[str, str]] = None,
    ) -> list[CommandResult]:
        """Execute a chain of commands."""
        results = []

        for command in commands:
            result = self.execute(command, cwd=cwd, env=env)
            results.append(result)

            if stop_on_failure and not result.success:
                logger.warning(f"Chain stopped at command: {command}")
                break

        return results

    def set_working_directory(self, path: str) -> bool:
        """Set the working directory for future commands."""
        if os.path.isdir(path):
            self._working_directory = path
            return True
        return False

    def set_environment_variable(self, key: str, value: str) -> None:
        """Set an environment variable."""
        self._environment[key] = value

    def get_working_directory(self) -> str:
        """Get the current working directory."""
        return self._working_directory

    def get_history(
        self,
        limit: Optional[int] = None,
    ) -> list[CommandResult]:
        """Get command execution history."""
        history = self._command_history
        if limit:
            history = history[-limit:]
        return history

    def clear_history(self) -> None:
        """Clear command execution history."""
        self._command_history.clear()
        self._command_counter = 0

    def parse_output(
        self,
        result: CommandResult,
        output_format: str = "text",
    ) -> Any:
        """Parse command output in various formats."""
        if output_format == "text":
            return result.stdout

        elif output_format == "lines":
            return result.stdout.strip().split("\n")

        elif output_format == "key_value":
            return self._parse_key_value(result.stdout)

        elif output_format == "json":
            return self._parse_json(result.stdout)

        else:
            return result.stdout

    def _parse_key_value(self, output: str) -> dict[str, str]:
        """Parse key=value output."""
        result = {}
        for line in output.strip().split("\n"):
            if "=" in line:
                key, value = line.split("=", 1)
                result[key.strip()] = value.strip()
        return result

    def _parse_json(self, output: str) -> Any:
        """Parse JSON output."""
        import json
        try:
            return json.loads(output)
        except json.JSONDecodeError:
            return {"raw": output}

    def get_statistics(self) -> dict[str, Any]:
        """Get shell execution statistics."""
        successful = sum(1 for r in self._command_history if r.success)
        return {
            "total_commands": len(self._command_history),
            "successful": successful,
            "failed": len(self._command_history) - successful,
            "avg_execution_time": (
                sum(r.execution_time for r in self._command_history) /
                len(self._command_history)
                if self._command_history else 0
            ),
        }


# Global instance
_enhanced_shell: Optional[EnhancedShell] = None


def get_enhanced_shell() -> EnhancedShell:
    """Get the global enhanced shell instance."""
    global _enhanced_shell
    if _enhanced_shell is None:
        _enhanced_shell = EnhancedShell()
    return _enhanced_shell
