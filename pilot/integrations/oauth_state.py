"""One pending Alibaba authorization at a time, kept in the database.

Alibaba's callback always carries `code` but its docs do not promise it echoes
`state` back. So a callback is accepted when either:
- it carries a `state` equal to the pending one, or
- it carries no `state` and an authorization was started from this app in the
  last 30 minutes (the lifetime of an Alibaba authorization code).
A callback with a *different* state is always rejected.
"""

from __future__ import annotations

import hmac
import secrets
import time

from .. import db

KEY = "alibaba_oauth_pending"
WINDOW = 30 * 60


def start() -> str:
    """Create (or reuse a recent) pending authorization and return its state."""
    pending = db.get_secret(KEY) or {}
    if pending.get("state") and time.time() - pending.get("created", 0) < WINDOW:
        return pending["state"]
    state = secrets.token_urlsafe(16)
    db.set_secret(KEY, {"state": state, "created": time.time()})
    return state


def accept(state: str | None) -> bool:
    pending = db.get_secret(KEY) or {}
    if not pending or time.time() - pending.get("created", 0) > WINDOW:
        return False
    if state:
        return hmac.compare_digest(state, pending.get("state", ""))
    return True


def clear() -> None:
    db.set_secret(KEY, {})
