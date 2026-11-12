"""Seller Control Center REST API: one API in front of Amazon SP-API and Alibaba.com.

Run:  uv run uvicorn api.main:app --port 8000      (docs at /docs)

Every route except /health, the Alibaba OAuth callback and the Alibaba webhook
needs the header `X-API-Key: $PILOT_API_KEY`. If PILOT_API_KEY is not set, those
routes are refused. Calls that change something outside this app (Amazon price,
Alibaba order, Alibaba payment link) also need `"confirm": true` in the body.
"""

from __future__ import annotations

import hmac
import json
import os
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from pilot import calc, db
from pilot.integrations import AlibabaError, AmazonError, factory, sync
from pilot.integrations.alibaba import READ_PATHS, verify_webhook

app = FastAPI(title="Seller Control Center API", version="1.0",
              description="Amazon UK selling + Alibaba sourcing in one API.")
db.init()


def require_key(x_api_key: str = Header(default="")) -> None:
    expected = os.environ.get("PILOT_API_KEY", "")
    if not expected:
        raise HTTPException(503, "Set PILOT_API_KEY on the server to enable the API.")
    if not hmac.compare_digest(x_api_key, expected):
        raise HTTPException(401, "Invalid or missing X-API-Key.")


@app.exception_handler(AmazonError)
async def _amazon_err(_: Request, e: AmazonError):
    from fastapi.responses import JSONResponse
    return JSONResponse({"source": "amazon", "error": str(e), "details": e.details},
                        status_code=502 if (e.status or 500) >= 500 else (e.status or 400))


@app.exception_handler(AlibabaError)
async def _alibaba_err(_: Request, e: AlibabaError):
    from fastapi.responses import JSONResponse
    return JSONResponse({"source": "alibaba", "error": str(e), "code": e.code,
                         "details": e.details}, status_code=400)


def _need_confirm(confirm: bool) -> None:
    if not confirm:
        raise HTTPException(400, "This changes something on Amazon/Alibaba. "
                                 "Resend with \"confirm\": true once approved.")


# ---------------------------------------------------------------- general
@app.get("/health")
def health():
    from pilot.integrations import AlibabaClient, AmazonClient
    return {"ok": True, "amazon_configured": AmazonClient.configured(),
            "alibaba_configured": AlibabaClient.configured(),
            "alibaba_authorized": bool(factory.alibaba_token_info())}


@app.get("/products", dependencies=[Depends(require_key)])
def products():
    s = db.get_settings()
    return [{**p, "economics": calc.unit_economics(p, s).__dict__} for p in db.records("products")]


# ---------------------------------------------------------------- amazon
@app.get("/amazon/status", dependencies=[Depends(require_key)])
def amazon_status():
    return {"marketplaces": factory.amazon().marketplace_participations()}


@app.get("/amazon/orders", dependencies=[Depends(require_key)])
def amazon_orders(days: int = Query(7, ge=1, le=90), status: list[str] | None = Query(None)):
    after = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%SZ")
    return factory.amazon().orders(after, status)


@app.get("/amazon/orders/{order_id}/items", dependencies=[Depends(require_key)])
def amazon_order_items(order_id: str):
    return factory.amazon().order_items(order_id)


@app.get("/amazon/inventory", dependencies=[Depends(require_key)])
def amazon_inventory(sku: list[str] | None = Query(None)):
    return factory.amazon().fba_inventory(sku)


@app.get("/amazon/fees/{asin}", dependencies=[Depends(require_key)])
def amazon_fees(asin: str, price: float = Query(..., gt=0), fba: bool = True):
    return factory.amazon().fees_estimate(asin, price, fba=fba)


@app.get("/amazon/offers/{asin}", dependencies=[Depends(require_key)])
def amazon_offers(asin: str):
    return factory.amazon().item_offers(asin)


@app.get("/amazon/catalog", dependencies=[Depends(require_key)])
def amazon_catalog(q: str = Query(..., min_length=2)):
    return factory.amazon().search_catalog(q)


class PriceChange(BaseModel):
    price: float = Field(gt=0)
    product_type: str = "PRODUCT"
    confirm: bool = False


@app.put("/amazon/listings/{sku}/price", dependencies=[Depends(require_key)])
def amazon_set_price(sku: str, body: PriceChange):
    _need_confirm(body.confirm)
    return factory.amazon().update_price(sku, body.price, body.product_type)


@app.post("/sync/amazon/fees", dependencies=[Depends(require_key)])
def sync_amazon_fees():
    """Replace estimated fees in Margins & prices with Amazon's real estimate (needs ASINs)."""
    return sync.sync_amazon_fees(factory.amazon())


# ---------------------------------------------------------------- alibaba
@app.get("/alibaba/auth/url", dependencies=[Depends(require_key)])
def alibaba_auth_url():
    state = secrets.token_urlsafe(16)
    db.set_secret("alibaba_oauth_state", state)
    return {"url": factory.alibaba().authorize_url(state)}


@app.get("/alibaba/callback", response_class=HTMLResponse)
def alibaba_callback(code: str, state: str = ""):
    """OAuth redirect target (set this URL as the app's callback in the App Console)."""
    expected = db.get_secret("alibaba_oauth_state", "")
    if not expected or not hmac.compare_digest(state, expected):
        raise HTTPException(400, "Unknown authorization request. Start again from /alibaba/auth/url.")
    db.set_secret("alibaba_oauth_state", "")
    t = factory.alibaba().create_token(code)
    return f"<h3>Alibaba account connected</h3><p>{t.get('user_nick', '')}</p>You can close this tab."


@app.get("/alibaba/status", dependencies=[Depends(require_key)])
def alibaba_status():
    return {"authorized": factory.alibaba_token_info()}


@app.post("/alibaba/token/refresh", dependencies=[Depends(require_key)])
def alibaba_refresh():
    factory.alibaba().refresh()
    return {"authorized": factory.alibaba_token_info()}


@app.get("/alibaba/search", dependencies=[Depends(require_key)])
def alibaba_search(q: str = Query(..., min_length=2), page: int = Query(1, ge=1),
                   size: int = Query(20, ge=1, le=50), ship_to: str = "GB"):
    return factory.alibaba().search(q, page=page, size=size, ship_to=ship_to)


@app.get("/alibaba/products/{product_id}", dependencies=[Depends(require_key)])
def alibaba_product(product_id: int, ship_to: str = "GB", currency: str = "USD"):
    return factory.alibaba().product(product_id, ship_to, currency)


@app.get("/alibaba/products/{product_id}/inventory", dependencies=[Depends(require_key)])
def alibaba_inventory(product_id: int, ship_to: str = "GB"):
    return factory.alibaba().inventory(product_id, ship_to)


@app.get("/alibaba/orders/{trade_id}", dependencies=[Depends(require_key)])
def alibaba_order(trade_id: str):
    return factory.alibaba().order(trade_id)


@app.get("/alibaba/orders/{trade_id}/tracking", dependencies=[Depends(require_key)])
def alibaba_tracking(trade_id: str):
    return factory.alibaba().tracking(trade_id)


class AlibabaCall(BaseModel):
    path: str
    params: dict = {}


@app.post("/alibaba/call", dependencies=[Depends(require_key)])
def alibaba_call(body: AlibabaCall):
    """Any read-only Alibaba buyer API (product pools, freight, order detail, tracking...)."""
    if body.path not in READ_PATHS:
        raise HTTPException(400, f"Path not allowed. Read-only paths: {sorted(READ_PATHS)}")
    return factory.alibaba().call(body.path, body.params)


class AlibabaOrder(BaseModel):
    order_request: dict
    confirm: bool = False


@app.post("/alibaba/orders", dependencies=[Depends(require_key)])
def alibaba_create_order(body: AlibabaOrder):
    _need_confirm(body.confirm)
    return factory.alibaba().create_order(body.order_request)


class AlibabaPay(BaseModel):
    order_ids: list[str]
    confirm: bool = False


@app.post("/alibaba/orders/pay", dependencies=[Depends(require_key)])
def alibaba_pay(body: AlibabaPay):
    """Returns a PayPal link for you to pay. Nothing is charged by this call."""
    _need_confirm(body.confirm)
    return factory.alibaba().payment_link(body.order_ids)


@app.post("/alibaba/webhook")
async def alibaba_webhook(request: Request, authorization: str = Header(default="")):
    """Product, price and order events pushed by Alibaba. Answer fast, store, de-duplicate."""
    raw = await request.body()
    key, secret = os.environ.get("ALIBABA_APP_KEY", ""), os.environ.get("ALIBABA_APP_SECRET", "")
    if not (key and secret and verify_webhook(raw, authorization, key, secret)):
        raise HTTPException(401, "Bad signature")
    try:
        msg = json.loads(raw)
    except ValueError:
        raise HTTPException(400, "Body is not JSON") from None
    data = msg.get("data") or {}
    dedup = "|".join(str(x) for x in (msg.get("message_type"), data.get("trade_id_str"),
                                      data.get("productId"), data.get("skuId"),
                                      data.get("option"), data.get("status"), data.get("value")))
    db.add_event("alibaba", str(msg.get("message_type")), dedup, raw.decode())
    return {"ok": True}
