import hashlib
import hmac
import json
import os
import tempfile
import unittest
from urllib.parse import parse_qs

os.environ["PILOT_DB"] = os.path.join(tempfile.mkdtemp(), "int.db")

import httpx  # noqa: E402

from pilot.integrations import alibaba, amazon  # noqa: E402


def amazon_mock(log):
    def handler(req: httpx.Request):
        log.append(req)
        if req.url.host == "api.amazon.com":
            return httpx.Response(200, json={"access_token": "Atza|tok", "expires_in": 3600})
        assert req.headers["x-amz-access-token"] == "Atza|tok"
        if req.url.path == "/orders/v0/orders":
            if "NextToken" in req.url.params:
                return httpx.Response(200, json={"payload": {"Orders": [{"AmazonOrderId": "2"}]}})
            return httpx.Response(200, json={"payload": {"Orders": [{"AmazonOrderId": "1"}],
                                                         "NextToken": "n"}})
        if req.url.path.endswith("/feesEstimate"):
            return httpx.Response(200, json={"payload": {"FeesEstimateResult": {
                "Status": "Success", "FeesEstimate": {
                    "TotalFeesEstimate": {"Amount": 4.75},
                    "FeeDetailList": [
                        {"FeeType": "ReferralFee", "FinalFee": {"Amount": 1.80}},
                        {"FeeType": "FBAFees", "FinalFee": {"Amount": 2.95}}]}}}})
        if req.method == "PATCH":
            return httpx.Response(200, json={"status": "ACCEPTED", "body": json.loads(req.content)})
        return httpx.Response(404, json={"errors": [{"message": "not found"}]})
    return httpx.Client(transport=httpx.MockTransport(handler))


class AmazonTests(unittest.TestCase):
    def client(self, log):
        return amazon.AmazonClient("id", "secret", "Atzr|refresh", seller_id="S1",
                                   http=amazon_mock(log))

    def test_token_cached_and_orders_paginate(self):
        log = []
        c = self.client(log)
        orders = c.orders("2026-11-01T00:00:00Z")
        self.assertEqual([o["AmazonOrderId"] for o in orders], ["1", "2"])
        self.assertEqual(sum(r.url.host == "api.amazon.com" for r in log), 1)
        self.assertEqual(log[1].url.host, "sellingpartnerapi-eu.amazon.com")
        self.assertEqual(log[1].url.params["MarketplaceIds"], amazon.UK_MARKETPLACE)

    def test_fees_estimate(self):
        est = self.client([]).fees_estimate("B000TEST", 11.99)
        self.assertEqual(est["fba"], 2.95)
        self.assertEqual(est["referral"], 1.80)

    def test_update_price_body(self):
        res = self.client([]).update_price("SKU-1", 10.99)
        offer = res["body"]["patches"][0]["value"][0]
        self.assertEqual(offer["our_price"][0]["schedule"][0]["value_with_tax"], 10.99)

    def test_error_is_raised(self):
        with self.assertRaises(amazon.AmazonError) as e:
            self.client([]).item_offers("B0NOPE")
        self.assertEqual(e.exception.status, 404)

    def test_sandbox_host(self):
        c = amazon.AmazonClient("a", "b", "c", sandbox=True, http=amazon_mock([]))
        self.assertTrue(c.base_url.startswith("https://sandbox.sellingpartnerapi-eu"))


class AlibabaTests(unittest.TestCase):
    def test_signature_matches_official_example(self):
        params = {"access_token": "test", "app_key": "123456", "order_id": "1234",
                  "sign_method": "sha256", "timestamp": "1517820392000"}
        self.assertEqual(alibaba.sign("/order/get", params, "helloworld"),
                         "4190D32361CFB9581350222F345CB77F3B19F0E31D162316848A2C1FFD5FAB4A")

    def test_webhook_verification(self):
        body = '{"message_type":3,"data":{"status":"paid"}}'
        good = hmac.new(b"sec", ("key" + body).encode(), hashlib.sha256).hexdigest()
        self.assertTrue(alibaba.verify_webhook(body, good, "key", "sec"))
        self.assertFalse(alibaba.verify_webhook(body, "00" * 32, "key", "sec"))

    def test_token_flow_and_signed_call(self):
        seen, saved = [], []

        def handler(req: httpx.Request):
            form = {k: v[0] for k, v in parse_qs(req.content.decode()).items()} if req.content \
                else dict(req.url.params)
            seen.append((req.url.path, form))
            path = req.url.path.removeprefix("/rest")
            self.assertEqual(form["sign"], alibaba.sign(path, form, "SECRET"))
            if path == "/auth/token/create":
                return httpx.Response(200, json={"code": "0", "access_token": "AT",
                                                 "refresh_token": "RT", "user_nick": "me"})
            if path == "/eco/buyer/product/description":
                self.assertEqual(form["access_token"], "AT")
                self.assertEqual(json.loads(form["query_req"])["product_id"], 1600)
                return httpx.Response(200, json={"code": "0", "result": {"title": "Stand"}})
            if path == "/eco/buyer/product/search":
                q = json.loads(form["param0"])
                self.assertEqual((q["keyword"], q["index"], q["shipToCountry"]), ("stand", 1, "GB"))
                return httpx.Response(200, json={"code": "0", "result": {"data": {
                    "products": [{"product_id": 1600, "title": "Stand", "price": "1.20-2.50"}],
                    "pagination": {"current": "1"}}}})
            return httpx.Response(200, json={"code": "IncompleteSignature", "message": "bad"})

        c = alibaba.AlibabaClient("KEY", "SECRET", on_tokens=saved.append,
                                  http=httpx.Client(transport=httpx.MockTransport(handler)))
        with self.assertRaises(alibaba.AlibabaError):
            c.product("1")  # not authorized yet
        c.create_token("3_500008_abc")
        self.assertEqual(saved[0]["refresh_token"], "RT")
        self.assertEqual(c.product("1600")["result"]["title"], "Stand")
        found = c.search("stand")["products"]
        self.assertEqual(alibaba.first_price(found[0]["price"]), 1.20)
        with self.assertRaises(alibaba.AlibabaError) as e:
            c.call("/unknown")
        self.assertEqual(e.exception.code, "IncompleteSignature")

    def test_first_price(self):
        self.assertEqual(alibaba.first_price("$3.5"), 3.5)
        self.assertIsNone(alibaba.first_price(None))

    def test_authorize_url(self):
        c = alibaba.AlibabaClient("KEY", "S", redirect_uri="https://x.test/cb")
        self.assertIn("client_id=KEY", c.authorize_url("st"))
        self.assertIn("redirect_uri=https%3A%2F%2Fx.test%2Fcb", c.authorize_url())


class ApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ.update(PILOT_API_KEY="k", ALIBABA_APP_KEY="key", ALIBABA_APP_SECRET="sec")
        from fastapi.testclient import TestClient

        import api.main as main
        from pilot import db
        cls.main, cls.db = main, db
        db.init(force_seed=True)
        cls.c = TestClient(main.app)
        main.factory.amazon = lambda: amazon.AmazonClient("i", "s", "r", seller_id="S1",
                                                          http=amazon_mock([]))

    def test_key_required(self):
        self.assertEqual(self.c.get("/health").status_code, 200)
        self.assertEqual(self.c.get("/products").status_code, 401)
        r = self.c.get("/products", headers={"X-API-Key": "k"})
        self.assertEqual(round(r.json()[0]["economics"]["profit"], 2), 1.64)

    def test_price_change_needs_confirm(self):
        h = {"X-API-Key": "k"}
        self.assertEqual(self.c.put("/amazon/listings/SKU/price", json={"price": 9.99},
                                    headers=h).status_code, 400)
        r = self.c.put("/amazon/listings/SKU/price", json={"price": 9.99, "confirm": True}, headers=h)
        self.assertEqual(r.status_code, 200, r.text)

    def test_sync_fees_updates_products(self):
        self.db.update("products", 1, {"asin": "B000TEST"})
        r = self.c.post("/sync/amazon/fees", headers={"X-API-Key": "k"}).json()
        self.assertEqual(r["updated"][0]["fba_fee"], 2.95)
        self.assertEqual(self.db.records("products")[0]["fba_fee"], 2.95)

    def test_alibaba_call_allowlist(self):
        r = self.c.post("/alibaba/call", json={"path": "/buynow/order/create"},
                        headers={"X-API-Key": "k"})
        self.assertEqual(r.status_code, 400)

    def test_webhook_signed_and_deduplicated(self):
        body = json.dumps({"message_type": 3, "data": {"status": "paid", "trade_id_str": "9"}})
        sig = hmac.new(b"sec", ("key" + body).encode(), hashlib.sha256).hexdigest()
        self.assertEqual(self.c.post("/alibaba/webhook", content=body,
                                     headers={"Authorization": "bad"}).status_code, 401)
        for _ in range(2):
            r = self.c.post("/alibaba/webhook", content=body, headers={"Authorization": sig})
            self.assertEqual(r.status_code, 200)
        self.assertEqual(len(self.db.events()), 1)

    def test_oauth_callback_rejects_unknown_state(self):
        self.assertEqual(self.c.get("/alibaba/callback?code=x&state=nope").status_code, 400)


if __name__ == "__main__":
    unittest.main()
