from __future__ import annotations

import hashlib
import hmac
import json
import logging
import time
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class MeshCredentials:
    token: str
    node_id: str


class MeshAuthenticator:
    def __init__(self, secret: Optional[str] = None):
        self._secret = secret or ""

    @property
    def enabled(self) -> bool:
        return bool(self._secret)

    def generate_challenge(self, node_id: str) -> tuple[str, float]:
        ts = time.time()
        raw = f"{node_id}:{ts}:{self._secret}"
        challenge = hashlib.sha256(raw.encode()).hexdigest()[:16]
        return challenge, ts

    def verify(self, node_id: str, challenge: str, ts: float, signature: str) -> bool:
        if not self.enabled:
            return True
        expected = hmac.new(
            self._secret.encode(),
            f"{node_id}:{challenge}:{ts}".encode(),
            hashlib.sha256,
        ).hexdigest()
        return hmac.compare_digest(expected, signature)

    def sign(self, node_id: str, challenge: str, ts: float = 0.0) -> str:
        ts = ts or time.time()
        return hmac.new(
            self._secret.encode(),
            f"{node_id}:{challenge}:{ts}".encode(),
            hashlib.sha256,
        ).hexdigest()

    def make_auth_payload(self, node_id: str) -> dict:
        challenge, ts = self.generate_challenge(node_id)
        signature = self.sign(node_id, challenge, ts)
        return {
            "node_id": node_id,
            "challenge": challenge,
            "timestamp": ts,
            "signature": signature,
        }

    def verify_auth_payload(self, payload: dict) -> bool:
        node_id = payload.get("node_id", "")
        challenge = payload.get("challenge", "")
        ts = payload.get("timestamp", 0.0)
        signature = payload.get("signature", "")
        return self.verify(node_id, challenge, ts, signature)
