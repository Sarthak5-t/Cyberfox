from __future__ import annotations

import json
import logging
import time
import threading
from dataclasses import dataclass, field
from typing import Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class SkillVersion:
    """A version of a skill."""
    version_id: str
    skill_id: str
    version: str
    changes: str
    parameters: dict[str, Any]
    created_at: float
    created_by: str
    is_active: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)


class SkillVersionManager:
    """Track skill evolution and support rollback."""

    def __init__(self, storage_dir: Optional[Path] = None):
        self._versions: dict[str, list[SkillVersion]] = {}
        self._lock = threading.RLock()
        self._storage_dir = storage_dir or Path.home() / ".cyberfox" / "ares" / "skill_versions"
        self._storage_dir.mkdir(parents=True, exist_ok=True)

    def create_version(
        self,
        skill_id: str,
        version: str,
        changes: str,
        parameters: dict[str, Any],
        created_by: str = "system",
        metadata: Optional[dict[str, Any]] = None,
    ) -> SkillVersion:
        """Create a new version of a skill."""
        with self._lock:
            version_id = f"v_{skill_id}_{version}"

            # Mark previous versions as inactive
            if skill_id in self._versions:
                for v in self._versions[skill_id]:
                    v.is_active = False

            new_version = SkillVersion(
                version_id=version_id,
                skill_id=skill_id,
                version=version,
                changes=changes,
                parameters=parameters,
                created_at=time.time(),
                created_by=created_by,
                is_active=True,
                metadata=metadata or {},
            )

            if skill_id not in self._versions:
                self._versions[skill_id] = []
            self._versions[skill_id].append(new_version)

            # Persist to disk
            self._persist_version(new_version)

            logger.info(f"Skill version created: {version_id}")
            return new_version

    def get_active_version(self, skill_id: str) -> Optional[SkillVersion]:
        """Get the active version of a skill."""
        with self._lock:
            if skill_id not in self._versions:
                return None

            for version in reversed(self._versions[skill_id]):
                if version.is_active:
                    return version
            return None

    def get_version(
        self,
        skill_id: str,
        version: str,
    ) -> Optional[SkillVersion]:
        """Get a specific version of a skill."""
        with self._lock:
            if skill_id not in self._versions:
                return None

            for v in self._versions[skill_id]:
                if v.version == version:
                    return v
            return None

    def get_all_versions(self, skill_id: str) -> list[SkillVersion]:
        """Get all versions of a skill."""
        with self._lock:
            return self._versions.get(skill_id, [])

    def rollback(
        self,
        skill_id: str,
        target_version: str,
    ) -> Optional[SkillVersion]:
        """Rollback to a previous version."""
        with self._lock:
            if skill_id not in self._versions:
                return None

            # Find the target version
            target = None
            for v in self._versions[skill_id]:
                if v.version == target_version:
                    target = v
                    break

            if not target:
                return None

            # Mark all versions as inactive
            for v in self._versions[skill_id]:
                v.is_active = False

            # Reactivate the target version
            target.is_active = True

            # Create a new version entry for the rollback
            rollback_version = f"{target.version}_rollback_{int(time.time())}"
            rollback = self.create_version(
                skill_id=skill_id,
                version=rollback_version,
                changes=f"Rollback to version {target_version}",
                parameters=target.parameters.copy(),
                created_by="system_rollback",
                metadata={"rollback_from": target_version},
            )

            logger.info(f"Skill rolled back: {skill_id} to {target_version}")
            return rollback

    def compare_versions(
        self,
        skill_id: str,
        version1: str,
        version2: str,
    ) -> dict[str, Any]:
        """Compare two versions of a skill."""
        v1 = self.get_version(skill_id, version1)
        v2 = self.get_version(skill_id, version2)

        if not v1 or not v2:
            return {"error": "One or both versions not found"}

        # Compare parameters
        param_diff = {}
        all_keys = set(v1.parameters.keys()) | set(v2.parameters.keys())
        for key in all_keys:
            v1_val = v1.parameters.get(key)
            v2_val = v2.parameters.get(key)
            if v1_val != v2_val:
                param_diff[key] = {"from": v1_val, "to": v2_val}

        return {
            "version_1": {
                "version": v1.version,
                "created_at": v1.created_at,
                "changes": v1.changes,
            },
            "version_2": {
                "version": v2.version,
                "created_at": v2.created_at,
                "changes": v2.changes,
            },
            "parameter_changes": param_diff,
            "has_changes": len(param_diff) > 0,
        }

    def get_version_history(
        self,
        skill_id: str,
    ) -> list[dict[str, Any]]:
        """Get version history for a skill."""
        versions = self.get_all_versions(skill_id)
        return [
            {
                "version": v.version,
                "changes": v.changes,
                "created_at": v.created_at,
                "created_by": v.created_by,
                "is_active": v.is_active,
            }
            for v in versions
        ]

    def get_statistics(self) -> dict[str, Any]:
        """Get versioning statistics."""
        with self._lock:
            stats = {
                "total_skills": len(self._versions),
                "total_versions": sum(
                    len(versions) for versions in self._versions.values()
                ),
                "avg_versions_per_skill": 0,
            }

            if self._versions:
                stats["avg_versions_per_skill"] = (
                    stats["total_versions"] / len(self._versions)
                )

            return stats

    def _persist_version(self, version: SkillVersion) -> None:
        """Persist version to disk."""
        try:
            skill_dir = self._storage_dir / version.skill_id
            skill_dir.mkdir(exist_ok=True)

            version_file = skill_dir / f"{version.version_id}.json"
            data = {
                "version_id": version.version_id,
                "skill_id": version.skill_id,
                "version": version.version,
                "changes": version.changes,
                "parameters": version.parameters,
                "created_at": version.created_at,
                "created_by": version.created_by,
                "is_active": version.is_active,
                "metadata": version.metadata,
            }
            version_file.write_text(json.dumps(data, indent=2))
            logger.debug(f"Version persisted to {version_file}")
        except Exception as e:
            logger.error(f"Failed to persist version: {e}")


# Global instance
_skill_version_manager: Optional[SkillVersionManager] = None


def get_skill_version_manager() -> SkillVersionManager:
    """Get the global skill version manager instance."""
    global _skill_version_manager
    if _skill_version_manager is None:
        _skill_version_manager = SkillVersionManager()
    return _skill_version_manager
