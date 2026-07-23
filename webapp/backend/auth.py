"""Lightweight single-password auth for the web app (single-machine, self-use).

If the env var ``TRADINGAGENTS_WEB_PASSWORD`` is set, the API requires a bearer
token obtained from ``POST /api/login`` with that password. Tokens are HMAC-signed
with the password (so no separate secret to manage) and carry an expiry, kept in
the token itself — there is no server-side session store.

If the env var is NOT set, auth is disabled and every request is allowed — this
preserves the current zero-config local experience. There is no user database and
no registration: it's one shared password, by design.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import os
import time

from fastapi import Header, HTTPException, Query

_ENV_KEY = "TRADINGAGENTS_WEB_PASSWORD"
_TTL_SECONDS = 7 * 24 * 3600  # a week; re-login after that


def auth_enabled() -> bool:
    return bool(os.environ.get(_ENV_KEY, "").strip())


def _password() -> str:
    return os.environ.get(_ENV_KEY, "").strip()


def _sign(payload: str) -> str:
    sig = hmac.new(_password().encode(), payload.encode(), hashlib.sha256).digest()
    return base64.urlsafe_b64encode(sig).decode().rstrip("=")


def issue_token() -> str:
    """Return a signed ``<expiry>.<sig>`` token valid for _TTL_SECONDS."""
    expiry = str(int(time.time()) + _TTL_SECONDS)
    return f"{expiry}.{_sign(expiry)}"


def verify_password(password: str) -> bool:
    return bool(password) and hmac.compare_digest(password.strip(), _password())


def _token_valid(token: str) -> bool:
    try:
        expiry, sig = token.split(".", 1)
    except ValueError:
        return False
    if not hmac.compare_digest(sig, _sign(expiry)):
        return False
    try:
        return int(expiry) >= int(time.time())
    except ValueError:
        return False


def require_auth(
    authorization: str | None = Header(default=None),
    token: str | None = Query(default=None),
) -> None:
    """FastAPI dependency: allow if auth is disabled or a valid token is present.

    Accepts the token either as an ``Authorization: Bearer <t>`` header (REST) or
    as a ``?token=<t>`` query param (SSE via EventSource, which can't set headers).
    """
    if not auth_enabled():
        return
    tok = (token or "").strip()
    if not tok and authorization and authorization.lower().startswith("bearer "):
        tok = authorization[7:].strip()
    if not _token_valid(tok):
        raise HTTPException(status_code=401, detail="login required")
