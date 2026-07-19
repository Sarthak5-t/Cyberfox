from __future__ import annotations

import base64
import hashlib
import hmac as _hmac
import json
import logging
import os
import struct
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_DEFAULT_STORE_DIR = Path.home() / ".cyberfox" / "ares"
_DEFAULT_STORE_NAME = "secrets.enc"

_DEFAULT_PASSPHRASE = "ares-default-change-me"

_HAS_CRYPTOGRAPHY = False
try:
    from cryptography.fernet import Fernet
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

    _HAS_CRYPTOGRAPHY = True
except ImportError:
    logger.warning(
        "cryptography library not available — falling back to "
        "hashlib+hmac obfuscation (NOT production-grade encryption)"
    )


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class SecretEntry:
    key: str
    value: str
    namespace: str = "default"
    created_at: float = field(default_factory=time.time)
    expires_at: float | None = None
    tags: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Fallback crypto (no `cryptography` library)
# ---------------------------------------------------------------------------

class _FallbackCrypto:
    """
    PBKDF2 + HMAC-SHA256 authenticated XOR stream cipher.
    NOT real encryption — protects against casual inspection only.
    """

    SALT_LEN = 32
    KEY_LEN = 32
    ROUNDS = 200_000
    IV_LEN = 16
    HMAC_LEN = 32

    @staticmethod
    def _derive(passphrase: str, salt: bytes) -> bytes:
        return hashlib.pbkdf2_hmac(
            "sha256",
            passphrase.encode("utf-8"),
            salt,
            _FallbackCrypto.ROUNDS,
            dklen=_FallbackCrypto.KEY_LEN,
        )

    @staticmethod
    def _xor_stream(key: bytes, iv: bytes, data_len: int) -> bytes:
        """Generate a pseudorandom keystream from key + iv."""
        block_count = (data_len + _FallbackCrypto.KEY_LEN - 1) // _FallbackCrypto.KEY_LEN
        ks = b""
        for i in range(block_count):
            block_seed = iv + struct.pack("<I", i)
            ks += _hmac.new(key, block_seed, hashlib.sha256).digest()
        return ks[:data_len]

    @classmethod
    def encrypt(cls, data: bytes, passphrase: str) -> bytes:
        salt = os.urandom(cls.SALT_LEN)
        key = cls._derive(passphrase, salt)
        iv = os.urandom(cls.IV_LEN)
        keystream = cls._xor_stream(key, iv, len(data))
        encrypted = bytes(a ^ b for a, b in zip(data, keystream))
        tag = _hmac.new(key, salt + iv + encrypted, hashlib.sha256).digest()
        return salt + iv + tag + encrypted

    @classmethod
    def decrypt(cls, data: bytes, passphrase: str) -> bytes:
        min_len = cls.SALT_LEN + cls.IV_LEN + cls.HMAC_LEN + 1
        if len(data) < min_len:
            raise ValueError("Data too short to be valid FallbackCrypto ciphertext")

        salt = data[: cls.SALT_LEN]
        iv = data[cls.SALT_LEN : cls.SALT_LEN + cls.IV_LEN]
        tag = data[cls.SALT_LEN + cls.IV_LEN : cls.SALT_LEN + cls.IV_LEN + cls.HMAC_LEN]
        encrypted = data[cls.SALT_LEN + cls.IV_LEN + cls.HMAC_LEN :]

        key = cls._derive(passphrase, salt)

        expected = _hmac.new(key, salt + iv + encrypted, hashlib.sha256).digest()
        if not _hmac.compare_digest(tag, expected):
            raise ValueError("Decryption failed — wrong passphrase or tampered data")

        keystream = cls._xor_stream(key, iv, len(encrypted))
        return bytes(a ^ b for a, b in zip(encrypted, keystream))


# ---------------------------------------------------------------------------
# SecretStore
# ---------------------------------------------------------------------------

class SecretStore:
    """
    Encrypted secrets store for Ares.

    Uses Fernet (AES-128-CBC + HMAC-SHA256) when the ``cryptography`` library
    is installed.  Falls back to a PBKDF2 + XOR scheme otherwise.
    """

    def __init__(self, store_path: str | Path | None = None) -> None:
        if store_path is None:
            store_path = _DEFAULT_STORE_DIR / _DEFAULT_STORE_NAME
        self._path = Path(store_path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._cache: dict[str, SecretEntry] | None = None
        self._cache_pass: str | None = None

    # ------------------------------------------------------------------
    # Internal helpers — encryption backends
    # ------------------------------------------------------------------

    @staticmethod
    def _derive_fernet_key(passphrase: str) -> bytes:
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b"ares-secrets-salt-v1",
            iterations=480_000,
        )
        return base64.urlsafe_b64encode(kdf.derive(passphrase.encode("utf-8")))

    @staticmethod
    def _encrypt(data: bytes, passphrase: str) -> bytes:
        if _HAS_CRYPTOGRAPHY:
            return Fernet(SecretStore._derive_fernet_key(passphrase)).encrypt(data)
        return _FallbackCrypto.encrypt(data, passphrase)

    @staticmethod
    def _decrypt(data: bytes, passphrase: str) -> bytes:
        if _HAS_CRYPTOGRAPHY:
            return Fernet(SecretStore._derive_fernet_key(passphrase)).decrypt(data)
        return _FallbackCrypto.decrypt(data, passphrase)

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _load_raw(self, passphrase: str) -> dict[str, SecretEntry]:
        if not self._path.exists():
            return {}

        raw_bytes = self._path.read_bytes()
        if not raw_bytes:
            return {}

        try:
            plaintext = self._decrypt(raw_bytes, passphrase)
        except Exception:
            logger.error("Failed to decrypt secrets store — wrong passphrase?")
            return {}

        data = json.loads(plaintext.decode("utf-8"))
        entries: dict[str, SecretEntry] = {}
        for ns, secrets in data.items():
            for _name, record in secrets.items():
                entry = SecretEntry(
                    key=record["key"],
                    value=record["value"],
                    namespace=record.get("namespace", ns),
                    created_at=record.get("created_at", 0.0),
                    expires_at=record.get("expires_at"),
                    tags=record.get("tags", []),
                )
                entries[f"{entry.namespace}:{entry.key}"] = entry
        return entries

    def _save_raw(self, entries: dict[str, SecretEntry], passphrase: str) -> bool:
        serialised: dict[str, dict[str, Any]] = {}
        for entry in entries.values():
            ns = entry.namespace
            if ns not in serialised:
                serialised[ns] = {}
            serialised[ns][entry.key] = {
                "key": entry.key,
                "value": entry.value,
                "namespace": entry.namespace,
                "created_at": entry.created_at,
                "expires_at": entry.expires_at,
                "tags": entry.tags,
            }

        plaintext = json.dumps(serialised, indent=2).encode("utf-8")
        try:
            ciphertext = self._encrypt(plaintext, passphrase)
            self._path.write_bytes(ciphertext)
            return True
        except Exception as exc:
            logger.error("Failed to save secrets store: %s", exc)
            return False

    def _load(self, passphrase: str) -> dict[str, SecretEntry]:
        if self._cache is not None and self._cache_pass == passphrase:
            return self._cache
        self._cache = self._load_raw(passphrase)
        self._cache_pass = passphrase
        return self._cache

    def _set_cache(self, entries: dict[str, SecretEntry], passphrase: str) -> None:
        self._cache = entries
        self._cache_pass = passphrase

    def _flush(self, passphrase: str) -> bool:
        if self._cache is None:
            return True
        ok = self._save_raw(self._cache, passphrase)
        if ok:
            logger.debug("Secrets store saved (%d entries)", len(self._cache))
        return ok

    @staticmethod
    def _is_expired(entry: SecretEntry) -> bool:
        if entry.expires_at is None:
            return False
        return time.time() > entry.expires_at

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def set_secret(
        self,
        key: str,
        value: str,
        namespace: str = "default",
        passphrase: str | None = None,
        expires_in: int | None = None,
    ) -> bool:
        pp = passphrase or os.environ.get("ARES_PASSPHRASE", _DEFAULT_PASSPHRASE)
        entries = self._load(pp)
        expires_at: float | None = None
        if expires_in is not None and expires_in > 0:
            expires_at = time.time() + expires_in
        entry = SecretEntry(
            key=key,
            value=value,
            namespace=namespace,
            expires_at=expires_at,
        )
        composite = f"{namespace}:{key}"
        entries[composite] = entry
        self._set_cache(entries, pp)
        ok = self._flush(pp)
        if ok:
            logger.info("Secret '%s' stored in namespace '%s'", key, namespace)
        return ok

    def get_secret(
        self,
        key: str,
        namespace: str = "default",
        passphrase: str | None = None,
    ) -> str | None:
        pp = passphrase or os.environ.get("ARES_PASSPHRASE", _DEFAULT_PASSPHRASE)
        entries = self._load(pp)
        composite = f"{namespace}:{key}"
        entry = entries.get(composite)
        if entry is None:
            logger.debug("Secret '%s' not found in namespace '%s'", key, namespace)
            return None
        if self._is_expired(entry):
            logger.info("Secret '%s' in namespace '%s' has expired — purging", key, namespace)
            del entries[composite]
            self._set_cache(entries, pp)
            self._flush(pp)
            return None
        return entry.value

    def delete_secret(
        self,
        key: str,
        namespace: str = "default",
        passphrase: str | None = None,
    ) -> bool:
        pp = passphrase or os.environ.get("ARES_PASSPHRASE", _DEFAULT_PASSPHRASE)
        entries = self._load(pp)
        composite = f"{namespace}:{key}"
        if composite not in entries:
            logger.debug("Secret '%s' not found for deletion", key)
            return False
        del entries[composite]
        self._set_cache(entries, pp)
        ok = self._flush(pp)
        if ok:
            logger.info("Deleted secret '%s' from namespace '%s'", key, namespace)
        return ok

    def list_secrets(
        self,
        namespace: str | None = None,
        passphrase: str | None = None,
    ) -> list[dict]:
        pp = passphrase or os.environ.get("ARES_PASSPHRASE", _DEFAULT_PASSPHRASE)
        entries = self._load(pp)
        result: list[dict] = []
        for entry in entries.values():
            if namespace is not None and entry.namespace != namespace:
                continue
            if self._is_expired(entry):
                continue
            result.append({
                "key": entry.key,
                "namespace": entry.namespace,
                "created_at": entry.created_at,
                "expires_at": entry.expires_at,
                "tags": entry.tags,
            })
        result.sort(key=lambda r: r["created_at"], reverse=True)
        return result

    def rotate_passphrase(self, old_passphrase: str, new_passphrase: str) -> bool:
        old_entries = self._load_raw(old_passphrase)
        if not old_entries:
            logger.warning("No entries found — nothing to rotate")
            return False
        self._set_cache(old_entries, old_passphrase)
        ok = self._save_raw(old_entries, new_passphrase)
        if ok:
            self._set_cache(self._load_raw(new_passphrase), new_passphrase)
            logger.info("Passphrase rotated — %d secrets re-encrypted", len(old_entries))
        return ok

    def export_secrets(self, namespace: str, passphrase: str) -> str | None:
        entries = self._load_raw(passphrase)
        export_data: list[dict] = []
        for entry in entries.values():
            if entry.namespace != namespace:
                continue
            if self._is_expired(entry):
                continue
            export_data.append({
                "key": entry.key,
                "value": entry.value,
                "namespace": entry.namespace,
                "created_at": entry.created_at,
                "expires_at": entry.expires_at,
                "tags": entry.tags,
            })
        if not export_data:
            logger.warning("No secrets found in namespace '%s' for export", namespace)
            return None
        plaintext = json.dumps(export_data, indent=2).encode("utf-8")
        try:
            ciphertext = self._encrypt(plaintext, passphrase)
            return base64.b64encode(ciphertext).decode("ascii")
        except Exception as exc:
            logger.error("Export failed: %s", exc)
            return None

    def import_secrets(self, data: str, passphrase: str) -> int:
        try:
            raw_bytes = base64.b64decode(data.encode("ascii"))
            plaintext = self._decrypt(raw_bytes, passphrase)
        except Exception as exc:
            logger.error("Import decryption failed: %s", exc)
            return 0

        try:
            import_list = json.loads(plaintext.decode("utf-8"))
        except json.JSONDecodeError as exc:
            logger.error("Import JSON decode failed: %s", exc)
            return 0

        entries = self._load(passphrase)
        count = 0
        for item in import_list:
            entry = SecretEntry(
                key=item["key"],
                value=item["value"],
                namespace=item.get("namespace", "default"),
                created_at=item.get("created_at", time.time()),
                expires_at=item.get("expires_at"),
                tags=item.get("tags", []),
            )
            composite = f"{entry.namespace}:{entry.key}"
            entries[composite] = entry
            count += 1

        self._set_cache(entries, passphrase)
        if self._flush(passphrase):
            logger.info("Imported %d secrets", count)
            return count
        return 0


# ---------------------------------------------------------------------------
# Module-level convenience
# ---------------------------------------------------------------------------

ARES_SECRETS = SecretStore()


def get_secret(
    key: str,
    namespace: str = "default",
    passphrase: str | None = None,
) -> str | None:
    return ARES_SECRETS.get_secret(key=key, namespace=namespace, passphrase=passphrase)


def set_secret(
    key: str,
    value: str,
    namespace: str = "default",
    passphrase: str | None = None,
) -> bool:
    return ARES_SECRETS.set_secret(key=key, value=value, namespace=namespace, passphrase=passphrase)
