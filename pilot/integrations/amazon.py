"""Amazon Selling Partner API (SP-API) client.

Auth: Login with Amazon (LWA). A refresh token is exchanged for a 1-hour access
token, sent as the `x-amz-access-token` header. AWS SigV4 signing is no longer
required by SP-API.

Credentials (environment variables):
  AMAZON_LWA_CLIENT_ID, AMAZON_LWA_CLIENT_SECRET, AMAZON_REFRESH_TOKEN,
  AMAZON_SELLER_ID (needed for listing/price updates),
  AMAZON_MARKETPLACE_ID (default A1F83G8C2ARO7P = amazon.co.uk),
  AMAZON_REGION (eu | na | fe, default eu), AMAZON_SANDBOX (1 to use the sandbox)
"""

from __future__ import annotations

import os
import time
from typing import Any

import httpx

LWA_TOKEN_URL = "https://api.amazon.com/auth/o2/token"
ENDPOINTS = {
    "na": "sellingpartnerapi-na.amazon.com",
    "eu": "sellingpartnerapi-eu.amazon.com",
    "fe": "sellingpartnerapi-fe.amazon.com",
}
UK_MARKETPLACE = "A1F83G8C2ARO7P"


class AmazonError(RuntimeError):
    def __init__(self, message: str, status: int | None = None, details: Any = None):
        super().__init__(message)
        self.status = status
        self.details = details


class AmazonClient:
    def __init__(self, client_id: str, client_secret: str, refresh_token: str, *,
                 seller_id: str = "", marketplace_id: str = UK_MARKETPLACE, region: str = "eu",
                 sandbox: bool = False, http: httpx.Client | None = None):
        if not (client_id and client_secret and refresh_token):
            raise AmazonError("Amazon credentials are missing (client id, secret, refresh token).")
        self.client_id, self.client_secret, self.refresh_token = client_id, client_secret, refresh_token
        self.seller_id = seller_id
        self.marketplace_id = marketplace_id
        host = ENDPOINTS[region]
        self.base_url = f"https://{'sandbox.' if sandbox else ''}{host}"
        self.http = http or httpx.Client(timeout=30)
        self._token: str | None = None
        self._token_expiry = 0.0

    @classmethod
    def from_env(cls, **kw) -> "AmazonClient":
        e = os.environ
        return cls(e.get("AMAZON_LWA_CLIENT_ID", ""), e.get("AMAZON_LWA_CLIENT_SECRET", ""),
                   e.get("AMAZON_REFRESH_TOKEN", ""), seller_id=e.get("AMAZON_SELLER_ID", ""),
                   marketplace_id=e.get("AMAZON_MARKETPLACE_ID", UK_MARKETPLACE),
                   region=e.get("AMAZON_REGION", "eu"),
                   sandbox=e.get("AMAZON_SANDBOX", "") in ("1", "true", "yes"), **kw)

    @staticmethod
    def configured() -> bool:
        return all(os.environ.get(k) for k in
                   ("AMAZON_LWA_CLIENT_ID", "AMAZON_LWA_CLIENT_SECRET", "AMAZON_REFRESH_TOKEN"))

    # ------------------------------------------------------------------ core
    def access_token(self) -> str:
        if self._token and time.time() < self._token_expiry - 60:
            return self._token
        r = self.http.post(LWA_TOKEN_URL, data={
            "grant_type": "refresh_token", "refresh_token": self.refresh_token,
            "client_id": self.client_id, "client_secret": self.client_secret})
        if r.status_code != 200:
            raise AmazonError("Login with Amazon token request failed", r.status_code, _json(r))
        data = r.json()
        self._token = data["access_token"]
        self._token_expiry = time.time() + int(data.get("expires_in", 3600))
        return self._token

    def request(self, method: str, path: str, *, params: dict | None = None,
                json: dict | None = None, retries: int = 3) -> dict:
        for attempt in range(retries):
            r = self.http.request(method, self.base_url + path, params=params, json=json, headers={
                "x-amz-access-token": self.access_token(), "accept": "application/json",
                "user-agent": "SellerControlCenter/1.0 (Language=Python)"})
            if r.status_code == 429 and attempt < retries - 1:  # throttled: back off
                time.sleep(2 ** attempt)
                continue
            if r.status_code >= 400:
                body = _json(r)
                msg = (body.get("errors") or [{}])[0].get("message") if isinstance(body, dict) else None
                raise AmazonError(msg or f"SP-API error {r.status_code}", r.status_code, body)
            return _json(r)
        raise AmazonError("SP-API throttled the request", 429)

    # ------------------------------------------------------------------ reads
    def marketplace_participations(self) -> list[dict]:
        """Cheapest call to check the connection works."""
        return self.request("GET", "/sellers/v1/marketplaceParticipations").get("payload", [])

    def orders(self, created_after: str, statuses: list[str] | None = None, max_results: int = 100) -> list[dict]:
        params = {"MarketplaceIds": self.marketplace_id, "CreatedAfter": created_after,
                  "MaxResultsPerPage": min(max_results, 100)}
        if statuses:
            params["OrderStatuses"] = ",".join(statuses)
        out: list[dict] = []
        while True:
            payload = self.request("GET", "/orders/v0/orders", params=params).get("payload", {})
            out += payload.get("Orders", [])
            token = payload.get("NextToken")
            if not token or len(out) >= max_results:
                return out[:max_results]
            params = {"MarketplaceIds": self.marketplace_id, "NextToken": token}

    def order_items(self, order_id: str) -> list[dict]:
        return self.request("GET", f"/orders/v0/orders/{order_id}/orderItems").get(
            "payload", {}).get("OrderItems", [])

    def fba_inventory(self, skus: list[str] | None = None) -> list[dict]:
        params: dict[str, Any] = {"details": "true", "granularityType": "Marketplace",
                                  "granularityId": self.marketplace_id,
                                  "marketplaceIds": self.marketplace_id}
        if skus:
            params["sellerSkus"] = ",".join(skus[:50])
        out: list[dict] = []
        while True:
            data = self.request("GET", "/fba/inventory/v1/summaries", params=params)
            out += data.get("payload", {}).get("inventorySummaries", [])
            token = (data.get("pagination") or {}).get("nextToken")
            if not token:
                return out
            params = {**params, "nextToken": token}

    def fees_estimate(self, asin: str, price: float, *, fba: bool = True, currency: str = "GBP") -> dict:
        """Amazon's own fee estimate (referral + FBA fulfilment) for a price."""
        body = {"FeesEstimateRequest": {
            "MarketplaceId": self.marketplace_id, "IsAmazonFulfilled": fba,
            "Identifier": f"{asin}-{price}",
            "PriceToEstimateFees": {"ListingPrice": {"CurrencyCode": currency, "Amount": price}}}}
        res = self.request("POST", f"/products/fees/v0/items/{asin}/feesEstimate", json=body)
        result = res.get("payload", {}).get("FeesEstimateResult", {})
        if result.get("Status") != "Success":
            raise AmazonError((result.get("Error") or {}).get("Message", "Fee estimate failed"),
                              details=result)
        est = result["FeesEstimate"]
        fees = {d["FeeType"]: d["FinalFee"]["Amount"] for d in est.get("FeeDetailList", [])}
        return {"total": est["TotalFeesEstimate"]["Amount"], "fees": fees,
                "referral": fees.get("ReferralFee", 0.0),
                "fba": fees.get("FBAFees", 0.0) or sum(v for k, v in fees.items() if "FBA" in k)}

    def item_offers(self, asin: str, condition: str = "New") -> dict:
        """Competing offers and Buy Box price for an ASIN."""
        return self.request("GET", f"/products/pricing/v0/items/{asin}/offers",
                            params={"MarketplaceId": self.marketplace_id,
                                    "ItemCondition": condition}).get("payload", {})

    def search_catalog(self, keywords: str, page_size: int = 10) -> list[dict]:
        data = self.request("GET", "/catalog/2022-04-01/items", params={
            "keywords": keywords, "marketplaceIds": self.marketplace_id, "pageSize": page_size,
            "includedData": "summaries,salesRanks,images"})
        return data.get("items", [])

    def listing(self, sku: str) -> dict:
        self._need_seller()
        return self.request("GET", f"/listings/2021-08-01/items/{self.seller_id}/{sku}",
                            params={"marketplaceIds": self.marketplace_id,
                                    "includedData": "summaries,attributes,issues,offers"})

    # ------------------------------------------------------------------ writes
    def update_price(self, sku: str, price: float, product_type: str = "PRODUCT", *,
                     currency: str = "GBP") -> dict:
        """Change a listing's price. Callers must get the seller's approval first."""
        self._need_seller()
        body = {"productType": product_type, "patches": [{
            "op": "replace", "path": "/attributes/purchasable_offer",
            "value": [{"marketplace_id": self.marketplace_id, "currency": currency,
                       "our_price": [{"schedule": [{"value_with_tax": round(price, 2)}]}]}]}]}
        return self.request("PATCH", f"/listings/2021-08-01/items/{self.seller_id}/{sku}",
                            params={"marketplaceIds": self.marketplace_id}, json=body)

    def _need_seller(self) -> None:
        if not self.seller_id:
            raise AmazonError("AMAZON_SELLER_ID is required for listing calls.")


def _json(r: httpx.Response) -> Any:
    try:
        return r.json()
    except ValueError:
        return {"raw": r.text}
