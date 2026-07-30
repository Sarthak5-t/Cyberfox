from __future__ import annotations

import logging
import subprocess
import time
from pathlib import Path

from cyberfox_constants import get_cyberfox_home as get_cf_home

logger = logging.getLogger(__name__)

REPO_URL = "https://github.com/0xMarcio/cve.git"
REPO_DIR_NAME = "cve_repo"


def repo_path() -> Path:
    return get_cf_home() / "ares" / REPO_DIR_NAME


def _git(*args: str, cwd: Path | None = None, timeout: int = 120) -> str:
    result = subprocess.run(
        ["git"] + list(args),
        cwd=str(cwd) if cwd else None,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    if result.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {result.stderr.strip()}")
    return result.stdout.strip()


def ensure_cloned() -> bool:
    path = repo_path()
    if (path / ".git").exists():
        return False
    logger.info("Cloning CVE repo from %s ...", REPO_URL)
    path.parent.mkdir(parents=True, exist_ok=True)
    _git("clone", "--depth", "1", REPO_URL, str(path))
    return True


def pull() -> dict:
    path = repo_path()
    if not (path / ".git").exists():
        was_cloned = ensure_cloned()
        return {"cloned": True, "pulled": False, "new_commits": 0, "error": None}

    try:
        before = _git("rev-parse", "HEAD", cwd=path)
        _git("pull", "--ff-only", "origin", "main", cwd=path)
        after = _git("rev-parse", "HEAD", cwd=path)
        new_commits = 0 if before == after else 1
        return {"cloned": False, "pulled": True, "new_commits": new_commits, "error": None}
    except RuntimeError as e:
        logger.warning("git pull failed: %s — attempting stash + pull", e)
        try:
            _git("stash", cwd=path)
            _git("pull", "--ff-only", "origin", "main", cwd=path)
            after = _git("rev-parse", "HEAD", cwd=path)
            return {"cloned": False, "pulled": True, "new_commits": 1, "error": "had local changes, stashed"}
        except RuntimeError as e2:
            logger.error("git pull still failed: %s", e2)
            return {"cloned": False, "pulled": False, "new_commits": 0, "error": str(e2)}


def clone_or_pull() -> dict:
    return pull()
