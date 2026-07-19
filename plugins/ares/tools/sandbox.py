from __future__ import annotations

import ctypes
import ctypes.util
import datetime
import logging
import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_LANDLOCK_ABI_VERSION = 1
_LANDLOCK_SYSCTL_PATH = "/proc/sys/kernel/unprivileged_userns_clone"
_LANDLOCK_AVAILABLE_PATH = "/sys/kernel/security/landlock"

# ---------------------------------------------------------------------------
# Data classes (forward-declared via __future__ annotations)
# ---------------------------------------------------------------------------


@dataclass
class JailSpec:
    allowed_paths: list[str] = field(default_factory=lambda: ["/tmp", "/usr", "/bin", "/var/tmp"])
    denied_paths: list[str] = field(default_factory=lambda: ["/etc", "/root", "/home", "/var/log"])
    max_temp_size_mb: int = 100
    network_allowed: bool = False
    timeout_secs: int = 600


@dataclass
class JailResult:
    success: bool
    sandbox_type: str  # "landlock" | "docker" | "chroot" | "none"
    enforced_paths: list[str]
    denied_paths: list[str]
    error: str | None = None


ARES_DEFAULT_JAIL = JailSpec(
    allowed_paths=["/tmp", "/usr", "/bin", "/var/tmp"],
    denied_paths=["/etc", "/root", "/home", "/var/log"],
    max_temp_size_mb=100,
    network_allowed=False,
    timeout_secs=600,
)

# ---------------------------------------------------------------------------
# Landlock ctypes bindings (subset)
# ---------------------------------------------------------------------------


class _LandlockRulesetAttr(ctypes.Structure):
    _fields_ = [
        ("handled_access_fs", ctypes.c_uint64),
    ]


class _LandlockPathBeneathAttr(ctypes.Structure):
    _fields_ = [
        ("allowed_access", ctypes.c_uint64),
        ("parent_fd", ctypes.c_int),
    ]


# Landlock access rights (from uapi/linux/landlock.h)
_LANDLOCK_ACCESS_FS_EXECUTE = 1 << 0
_LANDLOCK_ACCESS_FS_WRITE_FILE = 1 << 1
_LANDLOCK_ACCESS_FS_READ_FILE = 1 << 2
_LANDLOCK_ACCESS_FS_READ_DIR = 1 << 3
_LANDLOCK_ACCESS_FS_REMOVE_DIR = 1 << 4
_LANDLOCK_ACCESS_FS_REMOVE_FILE = 1 << 5
_LANDLOCK_ACCESS_FS_MAKE_CHAR = 1 << 6
_LANDLOCK_ACCESS_FS_MAKE_DIR = 1 << 7
_LANDLOCK_ACCESS_FS_MAKE_REG = 1 << 8
_LANDLOCK_ACCESS_FS_MAKE_SOCK = 1 << 9
_LANDLOCK_ACCESS_FS_MAKE_FIFO = 1 << 10
_LANDLOCK_ACCESS_FS_MAKE_BLOCK = 1 << 11
_LANDLOCK_ACCESS_FS_MAKE_SYM = 1 << 12
_LANDLOCK_ACCESS_FS_REFER = 1 << 13
_LANDLOCK_ACCESS_FS_TRUNCATE = 1 << 14

_LANDLOCK_ACCESS_FS_READ = _LANDLOCK_ACCESS_FS_READ_FILE | _LANDLOCK_ACCESS_FS_READ_DIR
_LANDLOCK_ACCESS_FS_WRITE = (
    _LANDLOCK_ACCESS_FS_WRITE_FILE
    | _LANDLOCK_ACCESS_FS_REMOVE_DIR
    | _LANDLOCK_ACCESS_FS_REMOVE_FILE
    | _LANDLOCK_ACCESS_FS_MAKE_CHAR
    | _LANDLOCK_ACCESS_FS_MAKE_DIR
    | _LANDLOCK_ACCESS_FS_MAKE_REG
    | _LANDLOCK_ACCESS_FS_MAKE_SOCK
    | _LANDLOCK_ACCESS_FS_MAKE_FIFO
    | _LANDLOCK_ACCESS_FS_MAKE_BLOCK
    | _LANDLOCK_ACCESS_FS_MAKE_SYM
    | _LANDLOCK_ACCESS_FS_TRUNCATE
)
_LANDLOCK_ACCESS_FS_FULL = _LANDLOCK_ACCESS_FS_READ | _LANDLOCK_ACCESS_FS_WRITE | _LANDLOCK_ACCESS_FS_EXECUTE


def _landlock_syscall(
    syscall_num: int,
    arg1: Any = 0,
    arg2: Any = 0,
    arg3: Any = 0,
    arg4: Any = 0,
    arg5: Any = 0,
) -> int:
    """Invoke a Landlock syscall via ctypes."""
    libc = ctypes.CDLL(ctypes.util.find_library("c") or "libc.so.6", use_errno=True)
    ret = libc.syscall(syscall_num, arg1, arg2, arg3, arg4, arg5)
    return ret


def _detect_landlock() -> bool:
    """Check whether Landlock LSM is available on this kernel."""
    # Check /sys/kernel/security/landlock exists
    if not os.path.isdir(_LANDLOCK_AVAILABLE_PATH):
        return False

    # Check unprivileged user namespace support (common gate)
    try:
        with open(_LANDLOCK_SYSCTL_PATH, "r") as f:
            val = f.read().strip()
            if val == "0":
                logger.debug("Landlock: unprivileged_userns_clone=0, may still work with root")
    except (OSError, FileNotFoundError):
        pass  # sysctl not present — newer kernels may not have it

    # Try to create a ruleset as a definitive test
    try:
        attr = _LandlockRulesetAttr(handled_access_fs=_LANDLOCK_ACCESS_FS_FULL)
        ruleset_fd = _landlock_syscall(444, ctypes.byref(attr), ctypes.sizeof(attr), 0)
        if ruleset_fd >= 0:
            libc = ctypes.CDLL(ctypes.util.find_library("c") or "libc.so.6", use_errno=True)
            libc.close(ruleset_fd)
            return True
        logger.debug("Landlock ruleset creation returned fd=%d errno=%d", ruleset_fd, ctypes.get_errno())
    except Exception as exc:
        logger.debug("Landlock detection failed: %s", exc)

    return False


# ---------------------------------------------------------------------------
# ToolSandbox
# ---------------------------------------------------------------------------


class ToolSandbox:
    """CWD jail sandbox for Ares tool subprocess calls.

    Uses a layered fallback strategy:
    1. Landlock LSM (kernel 5.13+) — best, least privileged
    2. Docker container — strong isolation
    3. chroot — legacy, weaker but widely available
    4. none — no confinement (last resort)
    """

    def __init__(self, spec: JailSpec | None = None, safe_mode: bool = False) -> None:
        self.spec = spec or JailSpec()
        self.safe_mode = safe_mode
        self._sandbox_type: str | None = None
        self._audit: list[dict[str, str]] = []
        self._enforced_paths: list[str] = []
        self._chroot_dir: str | None = None

    # ------------------------------------------------------------------
    # Detection
    # ------------------------------------------------------------------

    @staticmethod
    def detect_sandbox_type() -> str:
        """Return the best available sandbox type string."""
        if _detect_landlock():
            logger.info("Sandbox: Landlock LSM available")
            return "landlock"

        if shutil.which("docker"):
            try:
                result = subprocess.run(
                    ["docker", "info"],
                    capture_output=True,
                    timeout=10,
                )
                if result.returncode == 0:
                    logger.info("Sandbox: Docker daemon available")
                    return "docker"
            except (subprocess.TimeoutExpired, FileNotFoundError):
                pass

        if os.path.isdir("/usr") and os.access("/usr", os.R_OK):
            logger.info("Sandbox: chroot fallback available")
            return "chroot"

        logger.warning("Sandbox: no confinement available")
        return "none"

    # ------------------------------------------------------------------
    # Audit
    # ------------------------------------------------------------------

    def _log_audit(self, action: str, path: str, result: str) -> None:
        self._audit.append(
            {
                "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "action": action,
                "path": path,
                "result": result,
            }
        )

    def audit_log(self) -> list[dict[str, str]]:
        """Return the audit trail for this sandbox instance."""
        return list(self._audit)

    # ------------------------------------------------------------------
    # Landlock enforcement
    # ------------------------------------------------------------------

    def _enforce_landlock(self) -> JailResult:
        """Set up Landlock filesystem restrictions in the current process."""
        try:
            libc = ctypes.CDLL(ctypes.util.find_library("c") or "libc.so.6", use_errno=True)

            # Create ruleset
            attr = _LandlockRulesetAttr(handled_access_fs=_LANDLOCK_ACCESS_FS_FULL)
            ruleset_fd = _landlock_syscall(444, ctypes.byref(attr), ctypes.sizeof(attr), 0)
            if ruleset_fd < 0:
                errno = ctypes.get_errno()
                return JailResult(
                    success=False,
                    sandbox_type="landlock",
                    enforced_paths=[],
                    denied_paths=[],
                    error=f"landlock_create_ruleset failed: errno={errno}",
                )

            self._log_audit("ruleset_create", "/landlock", "ok")

            # Add allowed paths
            for path_str in self.spec.allowed_paths:
                path = Path(path_str).resolve()
                if not path.exists():
                    continue
                fd = os.open(str(path), os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
                pb = _LandlockPathBeneathAttr(
                    allowed_access=_LANDLOCK_ACCESS_FS_FULL,
                    parent_fd=fd,
                )
                ret = _landlock_syscall(445, ruleset_fd, ctypes.byref(pb), ctypes.sizeof(pb))
                os.close(fd)
                if ret == 0:
                    self._enforced_paths.append(str(path))
                    self._log_audit("allow_path", str(path), "ok")
                else:
                    self._log_audit("allow_path", str(path), f"errno={ctypes.get_errno()}")

            # Landlock does not have explicit deny rules — paths not added are
            # implicitly denied once the ruleset is committed.  We record denied
            # paths for audit/reporting.
            for path_str in self.spec.denied_paths:
                self._log_audit("deny_path", path_str, "implicit (not in allow list)")

            # Commit: restrict_self
            ret = _landlock_syscall(446, ruleset_fd, 0)
            libc.close(ruleset_fd)

            if ret != 0:
                return JailResult(
                    success=False,
                    sandbox_type="landlock",
                    enforced_paths=self._enforced_paths,
                    denied_paths=list(self.spec.denied_paths),
                    error=f"landlock_restrict_self failed: errno={ctypes.get_errno()}",
                )

            self._log_audit("restrict_self", "/", "ok")
            logger.info("Landlock: confinement active for %d paths", len(self._enforced_paths))

            return JailResult(
                success=True,
                sandbox_type="landlock",
                enforced_paths=list(self._enforced_paths),
                denied_paths=list(self.spec.denied_paths),
            )

        except Exception as exc:
            logger.error("Landlock enforcement failed: %s", exc)
            self._log_audit("landlock_error", "/", str(exc))
            return JailResult(
                success=False,
                sandbox_type="landlock",
                enforced_paths=[],
                denied_paths=[],
                error=str(exc),
            )

    # ------------------------------------------------------------------
    # Docker enforcement
    # ------------------------------------------------------------------

    def _build_docker_prefix(self, cwd: str | None = None) -> list[str]:
        """Build a ``docker run`` prefix that mirrors the JailSpec."""
        args: list[str] = [
            "docker", "run", "--rm", "--network=none",
        ]

        # Mount allowed paths as read-only (tools read /usr, /bin etc.)
        for p in self.spec.allowed_paths:
            if os.path.isdir(p):
                args += ["-v", f"{p}:{p}:ro"]

        # Mount a writable tmpdir for /tmp and /var/tmp
        tmp_dir = tempfile.mkdtemp(prefix="ares_jail_")
        os.chmod(tmp_dir, 0o755)
        args += ["-v", f"{tmp_dir}:/tmp:rw"]

        if "/var/tmp" in self.spec.allowed_paths:
            var_tmp = tempfile.mkdtemp(prefix="ares_vartmp_")
            os.chmod(var_tmp, 0o755)
            args += ["-v", f"{var_tmp}:/var/tmp:rw"]

        # Network
        if self.spec.network_allowed:
            # Replace --network=none with default bridge
            args = [a for a in args if a != "--network=none"]

        # Working directory
        if cwd:
            args += ["-w", cwd]

        # Drop capabilities
        args += ["--cap-drop=ALL"]

        # No new privileges
        args += ["--security-opt=no-new-privileges"]

        # Image placeholder (caller appends cmd after this)
        args += ["alpine:latest"]

        self._log_audit("docker_prefix", "/docker", "ok")
        return args

    # ------------------------------------------------------------------
    # chroot enforcement
    # ------------------------------------------------------------------

    def _setup_chroot(self) -> JailResult:
        """Prepare a minimal chroot jail under a temporary directory."""
        try:
            jail_dir = tempfile.mkdtemp(prefix="ares_chroot_")
            self._chroot_dir = jail_dir
            os.chmod(jail_dir, 0o755)

            # Reproduce allowed directories inside the jail
            for p in self.spec.allowed_paths:
                target = os.path.join(jail_dir, p.lstrip("/"))
                os.makedirs(target, exist_ok=True)
                self._log_audit("chroot_allow", p, target)
                self._enforced_paths.append(p)

            # Symlink essential binaries into the jail
            for binary in ("/bin/sh", "/bin/bash", "/usr/bin/env", "/usr/bin/python3"):
                if os.path.exists(binary):
                    link = os.path.join(jail_dir, binary.lstrip("/"))
                    link_dir = os.path.dirname(link)
                    os.makedirs(link_dir, exist_ok=True)
                    try:
                        os.link(binary, link)
                    except OSError:
                        shutil.copy2(binary, link)
                    self._log_audit("chroot_copy", binary, link)

            # Copy /etc essentials for basic shell functionality
            for subdir in ("etc", "lib", "lib64", "usr/lib", "usr/lib64"):
                src = f"/{subdir}"
                dst = os.path.join(jail_dir, subdir)
                if os.path.isdir(src) and not os.path.isdir(dst):
                    try:
                        shutil.copytree(src, dst, symlinks=True, dirs_exist_ok=True)
                    except (OSError, shutil.Error) as exc:
                        self._log_audit("chroot_copy_warn", src, str(exc))

            self._log_audit("chroot_setup", jail_dir, "ok")
            logger.info("chroot: jail prepared at %s", jail_dir)

            return JailResult(
                success=True,
                sandbox_type="chroot",
                enforced_paths=list(self._enforced_paths),
                denied_paths=list(self.spec.denied_paths),
            )

        except Exception as exc:
            logger.error("chroot setup failed: %s", exc)
            self._log_audit("chroot_error", "/", str(exc))
            return JailResult(
                success=False,
                sandbox_type="chroot",
                enforced_paths=[],
                denied_paths=[],
                error=str(exc),
            )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def enforce(self) -> JailResult:
        """Detect and activate the best available sandbox."""
        self._sandbox_type = self.detect_sandbox_type()
        self._log_audit("enforce", "/", self._sandbox_type)

        if self.safe_mode:
            self._log_audit("safe_mode", "/", "skipping real enforcement")
            for p in self.spec.allowed_paths:
                self._enforced_paths.append(p)
            return JailResult(
                success=True,
                sandbox_type=f"{self._sandbox_type}-safe",
                enforced_paths=list(self._enforced_paths),
                denied_paths=list(self.spec.denied_paths),
            )

        if self._sandbox_type == "landlock":
            return self._enforce_landlock()
        elif self._sandbox_type == "docker":
            # Docker doesn't require in-process setup; prefix built at wrap time.
            self._log_audit("docker_ready", "/", "prefix will be applied at wrap time")
            return JailResult(
                success=True,
                sandbox_type="docker",
                enforced_paths=list(self.spec.allowed_paths),
                denied_paths=list(self.spec.denied_paths),
            )
        elif self._sandbox_type == "chroot":
            return self._setup_chroot()
        else:
            self._log_audit("no_sandbox", "/", "proceeding unconfined")
            return JailResult(
                success=True,
                sandbox_type="none",
                enforced_paths=[],
                denied_paths=list(self.spec.denied_paths),
                error="no sandbox available — running unconfined",
            )

    # ------------------------------------------------------------------
    # Command wrapping
    # ------------------------------------------------------------------

    def wrap_command(self, cmd: str, cwd: str | None = None) -> str:
        """Wrap a shell command string with the active sandbox."""
        stype = self._sandbox_type or self.detect_sandbox_type()

        if stype == "docker":
            prefix_parts = self._build_docker_prefix(cwd)
            prefix = " ".join(prefix_parts)
            wrapped = f'{prefix} sh -c {repr(cmd)}'
            self._log_audit("wrap_command", cmd, "docker")
            return wrapped

        if stype == "chroot" and self._chroot_dir:
            escaped_cmd = cmd.replace("'", "'\\''")
            wrapped = f"chroot {self._chroot_dir} sh -c '{escaped_cmd}'"
            self._log_audit("wrap_command", cmd, "chroot")
            return wrapped

        # Landlock and none: run directly (Landlock restricts the process itself)
        self._log_audit("wrap_command", cmd, stype)
        return cmd

    def wrap_subprocess_args(self, argv: list[str], cwd: str | None = None) -> list[str]:
        """Return a ``subprocess.run``-compatible argv list with sandbox prefix."""
        stype = self._sandbox_type or self.detect_sandbox_type()

        if stype == "docker":
            prefix = self._build_docker_prefix(cwd)
            # Run argv as a command inside the container
            shell_cmd = " ".join(argv)
            return prefix + ["sh", "-c", shell_cmd]

        if stype == "chroot" and self._chroot_dir:
            # Rewrite paths relative to the chroot
            chroot_argv: list[str] = ["chroot", self._chroot_dir]
            for part in argv:
                abs_part = os.path.abspath(part)
                inside = os.path.join(self._chroot_dir, abs_part.lstrip("/"))
                if os.path.exists(abs_part) or "/" in part:
                    chroot_argv.append(inside)
                else:
                    chroot_argv.append(part)
            return chroot_argv

        # Landlock or none: pass through unchanged
        return list(argv)

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------

    def cleanup(self) -> None:
        """Remove temporary chroot directories."""
        if self._chroot_dir and os.path.isdir(self._chroot_dir):
            try:
                shutil.rmtree(self._chroot_dir)
                self._log_audit("cleanup", self._chroot_dir, "removed")
                logger.info("Sandbox: cleaned up chroot at %s", self._chroot_dir)
            except OSError as exc:
                logger.warning("Sandbox: failed to remove chroot %s: %s", self._chroot_dir, exc)
                self._log_audit("cleanup_error", self._chroot_dir, str(exc))
            self._chroot_dir = None

    def __del__(self) -> None:
        self.cleanup()


# ---------------------------------------------------------------------------
# Convenience function
# ---------------------------------------------------------------------------


def sandbox_subprocess(
    cmd: str,
    spec: JailSpec | None = None,
    timeout: int = 600,
    cwd: str | None = None,
) -> subprocess.CompletedProcess[str]:
    """Create a ToolSandbox, wrap *cmd*, and execute it.

    Returns a ``subprocess.CompletedProcess``.  The sandbox is cleaned up
    afterwards regardless of success/failure.
    """
    sandbox = ToolSandbox(spec)
    jail_result = sandbox.enforce()
    logger.info("Sandbox type=%s success=%s", jail_result.sandbox_type, jail_result.success)

    wrapped_cmd = sandbox.wrap_command(cmd, cwd=cwd)
    logger.debug("Wrapped command: %s", wrapped_cmd)

    try:
        result = subprocess.run(
            wrapped_cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=cwd,
        )
        return result
    except subprocess.TimeoutExpired:
        logger.error("Sandbox subprocess timed out after %ds", timeout)
        return subprocess.CompletedProcess(
            args=wrapped_cmd,
            returncode=-1,
            stdout="",
            stderr=f"Sandbox subprocess timed out after {timeout}s",
        )
    finally:
        sandbox.cleanup()
