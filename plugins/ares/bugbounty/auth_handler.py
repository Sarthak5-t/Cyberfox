from __future__ import annotations

import hashlib
import json
import logging
import time
import urllib.parse
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

SESSION_DIR = Path.home() / ".cyberfox" / "ares" / "sessions"


@dataclass
class AuthSession:
    target: str
    cookies: dict[str, str] = field(default_factory=dict)
    headers: dict[str, str] = field(default_factory=dict)
    auth_type: str = "none"  # none, form, basic, bearer, apikey
    username: str = ""
    login_url: str = ""
    expires_at: float = 0.0
    created_at: float = field(default_factory=time.time)
    csrf_token: str = ""
    csrf_field: str = "_token"
    is_valid: bool = True


class AuthHandler:
    """Session management for authenticated testing."""

    def __init__(self):
        self._sessions: dict[str, AuthSession] = {}
        SESSION_DIR.mkdir(parents=True, exist_ok=True)

    def _session_key(self, target: str) -> str:
        return target.lower().strip().rstrip("/")

    def login_form(self, target: str, login_url: str, username: str,
                   password: str, username_field: str = "username",
                   password_field: str = "password",
                   extra_fields: Optional[dict[str, str]] = None,
                   success_indicator: str = "logout") -> AuthSession:
        """Login via HTML form POST."""
        import subprocess

        key = self._session_key(target)
        session = AuthSession(target=target, login_url=login_url,
                              username=username, auth_type="form")

        # Build POST data
        post_data = {
            username_field: username,
            password_field: password,
        }
        if extra_fields:
            post_data.update(extra_fields)

        # First GET to capture CSRF token
        try:
            get_cmd = ["curl", "-sS", "-c", "-", login_url,
                        "-H", "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64)"]
            result = subprocess.run(get_cmd, capture_output=True, text=True, timeout=15)

            # Extract cookies from Set-Cookie headers
            for line in result.stdout.split("\n"):
                if line.startswith("#HttpOnly") or line.startswith("."):
                    parts = line.split("\t")
                    if len(parts) >= 7:
                        session.cookies[parts[5]] = parts[6]

            # Try to extract CSRF token from response
            csrf_patterns = [
                f'name="{session.csrf_field}" value="([^"]+)"',
                f'name="_csrf_token" value="([^"]+)"',
                f'name="csrf" value="([^"]+)"',
                f'"csrf":"([^"]+)"',
                f'"_token":"([^"]+)"',
            ]
            import re
            for pattern in csrf_patterns:
                match = re.search(pattern, result.stdout)
                if match:
                    post_data[session.csrf_field] = match.group(1)
                    session.csrf_token = match.group(1)
                    logger.info(f"CSRF token captured: {session.csrf_field}")
                    break
        except Exception as e:
            logger.warning(f"CSRF capture failed: {e}")

        # POST login
        try:
            cookie_str = "; ".join(f"{k}={v}" for k, v in session.cookies.items())
            post_fields = "&".join(f"{urllib.parse.quote(k)}={urllib.parse.quote(v)}"
                                   for k, v in post_data.items())

            login_cmd = [
                "curl", "-sS", "-L", "-D", "-",
                "-X", "POST", login_url,
                "-d", post_fields,
                "-H", "Content-Type: application/x-www-form-urlencoded",
                "-H", f"Cookie: {cookie_str}",
                "-H", "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
                "-c", "-",
            ]

            result = subprocess.run(login_cmd, capture_output=True, text=True, timeout=15)
            response = result.stdout.lower()

            # Parse new cookies from login response
            for line in result.stdout.split("\n"):
                line_lower = line.lower().strip()
                if line_lower.startswith("set-cookie:"):
                    cookie_part = line.split(":", 1)[1].split(";")[0].strip()
                    if "=" in cookie_part:
                        k, v = cookie_part.split("=", 1)
                        session.cookies[k.strip()] = v.strip()

            # Check if login succeeded
            if success_indicator.lower() in response:
                session.is_valid = True
                logger.info(f"Form login SUCCESS for {target} as {username}")
            else:
                logger.warning(f"Form login possibly FAILED for {target} - "
                               f"'{success_indicator}' not in response")

            # Build cookie and auth headers for requests
            session.headers["Cookie"] = "; ".join(f"{k}={v}" for k, v in session.cookies.items())

        except Exception as e:
            logger.error(f"Form login failed: {e}")

        self._sessions[key] = session
        self._save_session(key, session)
        return session

    def login_basic(self, target: str, username: str, password: str) -> AuthSession:
        """Login via HTTP Basic Auth."""
        key = self._session_key(target)
        import base64
        creds = base64.b64encode(f"{username}:{password}".encode()).decode()
        session = AuthSession(
            target=target, auth_type="basic", username=username,
            headers={"Authorization": f"Basic {creds}"}
        )
        self._sessions[key] = session
        logger.info(f"Basic auth configured for {target} as {username}")
        return session

    def login_bearer(self, target: str, token: str) -> AuthSession:
        """Login via Bearer token."""
        key = self._session_key(target)
        session = AuthSession(
            target=target, auth_type="bearer",
            headers={"Authorization": f"Bearer {token}"}
        )
        self._sessions[key] = session
        logger.info(f"Bearer auth configured for {target}")
        return session

    def login_apikey(self, target: str, key_name: str, key_value: str,
                     location: str = "header") -> AuthSession:
        """Login via API key."""
        skey = self._session_key(target)
        headers = {}
        if location == "header":
            headers[key_name] = key_value
        session = AuthSession(
            target=target, auth_type="apikey", username=key_name,
            headers=headers,
            cookies={key_name: key_value} if location == "cookie" else {}
        )
        self._sessions[skey] = session
        logger.info(f"API key configured for {target} ({location})")
        return session

    def get_session(self, target: str) -> Optional[AuthSession]:
        """Get active session for target."""
        key = self._session_key(target)
        session = self._sessions.get(key)
        if session and session.expires_at and time.time() > session.expires_at:
            session.is_valid = False
            logger.warning(f"Session expired for {target}")
            return None
        return session

    def get_auth_headers(self, target: str) -> dict[str, str]:
        """Get auth headers to inject into requests."""
        session = self.get_session(target)
        if not session:
            return {}
        return dict(session.headers)

    def get_curl_args(self, target: str) -> list[str]:
        """Get curl args for authenticated requests."""
        session = self.get_session(target)
        if not session:
            return []
        args = []
        if session.auth_type == "basic":
            args.extend(["-u", f"{session.username}:"])
        elif session.auth_type == "bearer":
            args.extend(["-H", f"Authorization: Bearer {session.headers.get('Authorization', '').split(' ')[-1]}"])
        elif session.cookies:
            cookie_str = "; ".join(f"{k}={v}" for k, v in session.cookies.items())
            args.extend(["-b", cookie_str])
        return args

    def invalidate(self, target: str) -> None:
        key = self._session_key(target)
        if key in self._sessions:
            self._sessions[key].is_valid = False
            del self._sessions[key]
            logger.info(f"Session invalidated for {target}")

    def is_authenticated(self, target: str) -> bool:
        session = self.get_session(target)
        return session is not None and session.is_valid

    def _save_session(self, key: str, session: AuthSession) -> None:
        try:
            data = {
                "target": session.target, "auth_type": session.auth_type,
                "username": session.username, "login_url": session.login_url,
                "cookies": session.cookies, "headers": session.headers,
                "created_at": session.created_at,
            }
            safe_key = hashlib.md5(key.encode()).hexdigest()[:12]
            path = SESSION_DIR / f"{safe_key}.json"
            path.write_text(json.dumps(data, indent=2))
        except Exception as e:
            logger.debug(f"Session save failed: {e}")


_auth_handler: Optional[AuthHandler] = None


def get_auth_handler() -> AuthHandler:
    global _auth_handler
    if _auth_handler is None:
        _auth_handler = AuthHandler()
    return _auth_handler
