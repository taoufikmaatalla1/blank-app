"""Build clients from environment variables, with Alibaba tokens kept in the database."""

from __future__ import annotations

from .. import db
from .alibaba import AlibabaClient
from .amazon import AmazonClient


def amazon() -> AmazonClient:
    return AmazonClient.from_env()


def alibaba() -> AlibabaClient:
    saved = db.get_secret("alibaba_tokens", {}) or {}
    kw = {k: saved[k] for k in ("access_token", "refresh_token") if saved.get(k)}
    return AlibabaClient.from_env(on_tokens=lambda t: db.set_secret("alibaba_tokens", t), **kw)


def alibaba_token_info() -> dict:
    t = db.get_secret("alibaba_tokens", {}) or {}
    return {k: t.get(k) for k in ("user_nick", "account", "buyer_id", "expires_in",
                                  "refresh_expires_in", "obtained_at")} if t else {}
