from __future__ import annotations

import logging
import os
import signal
import subprocess
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Optional, Callable
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class ProcessInfo:
    """Information about a managed process."""
    process_id: str
    pid: Optional[int]
    command: str
    status: str  # "running", "completed", "failed", "killed"
    start_time: float
    end_time: Optional[float] = None
    return_code: Optional[int] = None
    stdout: str = ""
    stderr: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


class ProcessManager:
    """Manage process lifecycle: start, stop, monitor, cleanup."""

    def __init__(self):
        self._processes: dict[str, ProcessInfo] = {}
        self._subprocesses: dict[str, subprocess.Popen] = {}
        self._lock = threading.Lock()
        self._process_counter = 0
        self._cleanup_interval = 300  # 5 minutes
        self._last_cleanup = time.time()

    def start_process(
        self,
        command: str,
        cwd: Optional[str] = None,
        env: Optional[dict[str, str]] = None,
        timeout: Optional[float] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> ProcessInfo:
        """Start a new process."""
        with self._lock:
            self._process_counter += 1
            process_id = f"proc_{self._process_counter}"

            try:
                # Prepare environment
                process_env = os.environ.copy()
                if env:
                    process_env.update(env)

                # Start process
                proc = subprocess.Popen(
                    command,
                    shell=True,
                    cwd=cwd,
                    env=process_env,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                )

                process_info = ProcessInfo(
                    process_id=process_id,
                    pid=proc.pid,
                    command=command,
                    status="running",
                    start_time=time.time(),
                    metadata=metadata or {},
                )

                self._processes[process_id] = process_info
                self._subprocesses[process_id] = proc

                # Start monitoring thread if timeout specified
                if timeout:
                    monitor_thread = threading.Thread(
                        target=self._monitor_process,
                        args=(process_id, timeout),
                        daemon=True,
                    )
                    monitor_thread.start()

                logger.info(f"Process started: {process_id} (PID: {proc.pid})")
                return process_info

            except Exception as e:
                process_info = ProcessInfo(
                    process_id=process_id,
                    pid=None,
                    command=command,
                    status="failed",
                    start_time=time.time(),
                    end_time=time.time(),
                    stderr=str(e),
                    metadata=metadata or {},
                )
                self._processes[process_id] = process_info
                logger.error(f"Failed to start process: {e}")
                return process_info

    def stop_process(
        self,
        process_id: str,
        force: bool = False,
    ) -> bool:
        """Stop a running process."""
        with self._lock:
            if process_id not in self._subprocesses:
                return False

            proc = self._subprocesses[process_id]
            process_info = self._processes[process_id]

            try:
                if force:
                    proc.kill()
                else:
                    proc.terminate()

                # Wait for process to terminate
                try:
                    stdout, stderr = proc.communicate(timeout=10)
                    process_info.stdout = stdout or ""
                    process_info.stderr = stderr or ""
                except subprocess.TimeoutExpired:
                    proc.kill()
                    stdout, stderr = proc.communicate()
                    process_info.stdout = stdout or ""
                    process_info.stderr = stderr or ""

                process_info.status = "completed"
                process_info.end_time = time.time()
                process_info.return_code = proc.returncode

                del self._subprocesses[process_id]
                logger.info(f"Process stopped: {process_id}")
                return True

            except Exception as e:
                logger.error(f"Failed to stop process {process_id}: {e}")
                return False

    def kill_process(self, process_id: str) -> bool:
        """Forcefully kill a process."""
        return self.stop_process(process_id, force=True)

    def get_process(self, process_id: str) -> Optional[ProcessInfo]:
        """Get process information."""
        return self._processes.get(process_id)

    def list_processes(
        self,
        status: Optional[str] = None,
    ) -> list[ProcessInfo]:
        """List all processes, optionally filtered by status."""
        with self._lock:
            processes = list(self._processes.values())
            if status:
                processes = [p for p in processes if p.status == status]
            return processes

    def wait_for_process(
        self,
        process_id: str,
        timeout: Optional[float] = None,
    ) -> Optional[ProcessInfo]:
        """Wait for a process to complete."""
        with self._lock:
            if process_id not in self._subprocesses:
                return self._processes.get(process_id)

            proc = self._subprocesses[process_id]

        try:
            stdout, stderr = proc.communicate(timeout=timeout)
            with self._lock:
                process_info = self._processes[process_id]
                process_info.stdout = stdout or ""
                process_info.stderr = stderr or ""
                process_info.status = "completed"
                process_info.end_time = time.time()
                process_info.return_code = proc.returncode

                if process_id in self._subprocesses:
                    del self._subprocesses[process_id]

            return process_info

        except subprocess.TimeoutExpired:
            logger.warning(f"Process {process_id} timed out")
            return None

        except Exception as e:
            logger.error(f"Error waiting for process {process_id}: {e}")
            return None

    def _monitor_process(self, process_id: str, timeout: float) -> None:
        """Monitor a process and kill it if it exceeds timeout."""
        start_time = time.time()
        while time.time() - start_time < timeout:
            with self._lock:
                if process_id not in self._subprocesses:
                    return
                proc = self._subprocesses[process_id]

            if proc.poll() is not None:
                return

            time.sleep(0.1)

        # Timeout exceeded, kill process
        logger.warning(f"Process {process_id} exceeded timeout ({timeout}s)")
        self.kill_process(process_id)

    def cleanup_old_processes(self) -> int:
        """Cleanup old completed processes."""
        now = time.time()
        if now - self._last_cleanup < self._cleanup_interval:
            return 0

        self._last_cleanup = now
        cleaned = 0

        with self._lock:
            to_remove = []
            for process_id, info in self._processes.items():
                if info.status in ("completed", "failed") and info.end_time:
                    if now - info.end_time > 3600:  # 1 hour
                        to_remove.append(process_id)

            for process_id in to_remove:
                del self._processes[process_id]
                cleaned += 1

        return cleaned

    def get_statistics(self) -> dict[str, Any]:
        """Get process manager statistics."""
        with self._lock:
            return {
                "total_processes": len(self._processes),
                "running": sum(1 for p in self._processes.values() if p.status == "running"),
                "completed": sum(1 for p in self._processes.values() if p.status == "completed"),
                "failed": sum(1 for p in self._processes.values() if p.status == "failed"),
            }


# Global instance
_process_manager: Optional[ProcessManager] = None


def get_process_manager() -> ProcessManager:
    """Get the global process manager instance."""
    global _process_manager
    if _process_manager is None:
        _process_manager = ProcessManager()
    return _process_manager
