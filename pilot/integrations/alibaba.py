"""Alibaba.com Open Platform client (buyer / ISV-dropshipping APIs).

Setup (once): register a *buyer* account at openapi.alibaba.com with a country
outside mainland China, create an app (category ISV-Dropshipping) in the App
Console to get an AppKey/AppSecret, set its callback URL, and request the API
permission groups you need. Then the buyer authorizes the app with OAuth 2.0.

Credentials (environment variables):
  ALIBABA_APP_KEY, ALIBABA_APP_SECRET, ALIBABA_REDIRECT_URI
  ALIBABA_ACCESS_TOKEN / ALIBABA_REFRESH_TOKEN (optional; normally stored by the app)

Every call is signed: sort all parameters by name, concatenate name+value, put the
API path in front, HMAC-SHA256 with the AppSecret, upper-case hex.
"""

from __future__ import annotations

import hashlib
import hmac
import json as _jsonlib
import os
import time
from typing import Any, Callable
from urllib.parse import urlencode

import httpx

GATEWAY = "https://openapi-api.alibaba.com/rest"
AUTHORIZE_URL = "https://openapi-auth.alibaba.com/oauth/authorize"

# Read-only paths the generic `call` endpoint of the REST API may forward.
READ_PATHS = {
    "/eco/buyer/product/search", "/eco/buyer/product/check", "/eco/buyer/local/product/check",
    "/eco/buyer/product/keyattributes", "/alibaba/order/list", "/eco/buyer/product/description",
    "/eco/buyer/product/batch/description", "/eco/buyer/product/inventory",
    "/eco/buyer/product/batch/inventory", "/eco/buyer/product/cert", "/warehouse/list",
    "/shipping/freight/calculate", "/order/freight/calculate", "/alibaba/order/get",
    "/alibaba/order/pay/result/query", "/order/logistics/tracking/get",
    "/order/logistics/query", "/alibaba/order/fund/query",
}
# Paths that create orders or start payments: only called after explicit approval.
WRITE_PATHS = {"/buynow/order/create", "/alibaba/dropshipping/order/pay"}


class AlibabaError(RuntimeError):
    def __init__(self, message: str, code: str | None = None, details: Any = None):
        super().__init__(message)
        self.code = code
        self.details = details


def sign(api_path: str, params: dict[str, Any], app_secret: str) -> str:
    base = api_path + "".join(f"{k}{params[k]}" for k in sorted(params) if k != "sign")
    return hmac.new(app_secret.encode(), base.encode(), hashlib.sha256).hexdigest().upper()


def verify_webhook(body: bytes | str, authorization: str, app_key: str, app_secret: str) -> bool:
    """Check the Authorization header of a pushed message: hex HMAC-SHA256(app_key + body)."""
    if isinstance(body, bytes):
        body = body.decode()
    expected = hmac.new(app_secret.encode(), (app_key + body).encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected.lower(), (authorization or "").lower())


class AlibabaClient:
    def __init__(self, app_key: str, app_secret: str, *, access_token: str = "",
                 refresh_token: str = "", redirect_uri: str = "", gateway: str = GATEWAY,
                 on_tokens: Callable[[dict], None] | None = None, http: httpx.Client | None = None):
        if not (app_key and app_secret):
            raise AlibabaError("Alibaba AppKey and AppSecret are missing.")
        self.app_key, self.app_secret = app_key, app_secret
        self.access_token, self.refresh_token = access_token, refresh_token
        self.redirect_uri = redirect_uri
        self.gateway = gateway.rstrip("/")
        self.on_tokens = on_tokens  # called with the token response so it can be saved
        self.http = http or httpx.Client(timeout=30)

    @classmethod
    def from_env(cls, **kw) -> "AlibabaClient":
        e = os.environ
        kw.setdefault("access_token", e.get("ALIBABA_ACCESS_TOKEN", ""))
        kw.setdefault("refresh_token", e.get("ALIBABA_REFRESH_TOKEN", ""))
        return cls(e.get("ALIBABA_APP_KEY", ""), e.get("ALIBABA_APP_SECRET", ""),
                   redirect_uri=e.get("ALIBABA_REDIRECT_URI", ""), **kw)

    @staticmethod
    def configured() -> bool:
        return bool(os.environ.get("ALIBABA_APP_KEY") and os.environ.get("ALIBABA_APP_SECRET"))

    # ------------------------------------------------------------------ core
    def call(self, api_path: str, params: dict[str, Any] | None = None, *,
             auth: bool = True, method: str = "POST") -> dict:
        p: dict[str, Any] = {"app_key": self.app_key, "sign_method": "sha256",
                             "timestamp": str(int(time.time() * 1000))}
        if auth:
            if not self.access_token:
                raise AlibabaError("Not authorized yet: connect your Alibaba buyer account first.")
            p["access_token"] = self.access_token
        for k, v in (params or {}).items():
            if v is None:
                continue
            p[k] = _jsonlib.dumps(v, separators=(",", ":")) if isinstance(v, (dict, list)) else str(v)
        p["sign"] = sign(api_path, p, self.app_secret)
        url = self.gateway + api_path
        r = (self.http.get(url, params=p) if method == "GET"
             else self.http.post(url, data=p))
        try:
            data = r.json()
        except ValueError:
            raise AlibabaError(f"Alibaba returned HTTP {r.status_code}", details=r.text) from None
        code = str(data.get("code", "0"))
        if r.status_code >= 400 or code not in ("0", ""):
            raise AlibabaError(data.get("message") or data.get("msg") or f"Alibaba error {code}",
                               code, data)
        return data

    # ------------------------------------------------------------------ OAuth
    def authorize_url(self, state: str = "") -> str:
        q = {"response_type": "code", "client_id": self.app_key, "redirect_uri": self.redirect_uri}
        if state:
            q["state"] = state
        return f"{AUTHORIZE_URL}?{urlencode(q)}"

    def create_token(self, code: str) -> dict:
        """Exchange the code from the OAuth callback (valid 30 minutes) for tokens."""
        return self._store(self.call("/auth/token/create", {"code": code}, auth=False))

    def refresh(self) -> dict:
        if not self.refresh_token:
            raise AlibabaError("No refresh token: authorize the buyer account again.")
        return self._store(self.call("/auth/token/refresh",
                                     {"refresh_token": self.refresh_token}, auth=False))

    def _store(self, data: dict) -> dict:
        self.access_token = data.get("access_token", self.access_token)
        self.refresh_token = data.get("refresh_token", self.refresh_token)
        data["obtained_at"] = int(time.time())
        if self.on_tokens:
            self.on_tokens(data)
        return data

    # ------------------------------------------------------------------ products
    def search(self, keyword: str, *, page: int = 1, size: int = 20, ship_to: str = "GB",
               currency: str = "USD", product_type: str | None = None) -> dict:
        """Keyword search. Returns {products: [...], pagination: {...}}."""
        q = {"keyword": keyword, "index": page, "size": min(size, 50), "shipToCountry": ship_to,
             "currency": currency, "language": "en", "productType": product_type}
        res = self.call("/eco/buyer/product/search",
                        {"param0": {k: v for k, v in q.items() if v is not None}}, method="GET")
        data = (res.get("result") or {}).get("data") or res.get("data") or {}
        return {"products": data.get("products", []), "pagination": data.get("pagination", {})}

    def product_list(self, product_type: str, *, index: int = 0, size: int = 100) -> dict:
        """Product IDs from a curated pool, e.g. EU_GGS_Normal, TOP_DEALS."""
        return self.call("/eco/buyer/product/check", {"query_req": {
            "product_type": product_type, "index": index, "size": min(size, 300)}}, method="GET")

    def product(self, product_id: str | int, ship_to: str = "GB", currency: str = "USD") -> dict:
        return self.call("/eco/buyer/product/description", {"query_req": {
            "product_id": int(product_id), "country": ship_to, "ship_to_country": ship_to,
            "currency": currency, "language": "en-US"}}, method="GET")

    def inventory(self, product_id: str | int, ship_to: str = "GB", shipping_from: str = "CN") -> dict:
        return self.call("/eco/buyer/product/inventory", {"inv_req": {
            "product_id": int(product_id), "ship_to": ship_to, "shipping_from": shipping_from}},
            method="GET")

    def certificates(self, product_id: str | int) -> dict:
        return self.call("/eco/buyer/product/cert", {"product_id": int(product_id)}, method="GET")

    # ------------------------------------------------------------------ orders
    def create_order(self, order_request: dict) -> dict:
        """Create a BuyNow order. Callers must get the buyer's approval first."""
        return self.call("/buynow/order/create", order_request)

    def payment_link(self, order_ids: list[int | str], method: str = "PAYPAL") -> dict:
        """Returns a PayPal URL the buyer opens to pay. Nothing is charged by this call."""
        return self.call("/alibaba/dropshipping/order/pay",
                         {"order_id_list": [int(i) for i in order_ids], "payment_method": method})

    def order(self, trade_id: str | int) -> dict:
        return self.call("/alibaba/order/get", {"e_trade_id": str(trade_id), "language": "en_US"})

    def tracking(self, trade_id: str | int) -> dict:
        return self.call("/order/logistics/tracking/get", {"trade_id": int(trade_id)})


def first_price(price: Any) -> float | None:
    """Alibaba prices can be ranges like '1.20-2.50' or '$1.20'; take the first number."""
    import re
    m = re.search(r"\d+(?:\.\d+)?", str(price or ""))
    return float(m.group()) if m else None
