"""'Connections' tab: live Amazon SP-API and Alibaba.com data inside the app."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pandas as pd
import streamlit as st

from . import db
from .integrations import AlibabaClient, AlibabaError, AmazonClient, AmazonError, factory, sync
from .integrations.alibaba import first_price

AMAZON_SETUP = """
1. In Seller Central go to **Apps and Services → Develop Apps** and register as a developer
   (private seller application).
2. Create an app client. Note its **LWA client ID** and **client secret**.
3. Click **Authorize** next to the app to get a **refresh token** for your store.
4. Set these environment variables where the app runs (on Streamlit Community Cloud,
   put them in *Settings → Secrets*):
   `AMAZON_LWA_CLIENT_ID`, `AMAZON_LWA_CLIENT_SECRET`, `AMAZON_REFRESH_TOKEN`,
   `AMAZON_SELLER_ID` (Merchant Token, under Settings → Account Info → Business information).
5. Optional: `AMAZON_SANDBOX=1` to try the API against Amazon's test data first.
"""

ALIBABA_SETUP = """
1. Sign up as a **buyer** at [openapi.alibaba.com](https://openapi.alibaba.com/) with a country
   **outside mainland China** (it cannot be changed later; China accounts cannot place orders).
2. Log in again, activate the Open Platform account, then create an app in the
   [App Console](https://openapi.alibaba.com/app/index.htm) with category **ISV-Dropshipping**.
3. Request the **API permission groups** you need (products, orders, logistics);
   without them every call answers "no permission".
4. Set the app's callback URL to this app's address (or the API's `/alibaba/callback`).
5. Set `ALIBABA_APP_KEY`, `ALIBABA_APP_SECRET` and `ALIBABA_REDIRECT_URI` (the same callback URL).
"""


def _error(e: Exception) -> None:
    st.error(f"{e}")
    details = getattr(e, "details", None)
    if details:
        with st.expander("Details"):
            st.json(details)


def _handle_alibaba_callback() -> None:
    """If Alibaba redirected back here with ?code=..., exchange it for tokens."""
    qp = st.query_params
    if "code" not in qp or not AlibabaClient.configured():
        return
    code, state = qp.get("code"), qp.get("state", "")
    expected = db.get_secret("alibaba_oauth_state", "")
    st.query_params.clear()
    if not expected or state != expected:
        st.warning("Ignored an Alibaba authorization that did not start from this app.")
        return
    try:
        t = factory.alibaba().create_token(code)
        db.set_secret("alibaba_oauth_state", "")
        st.success(f"Alibaba account connected: {t.get('user_nick') or t.get('account') or ''}")
    except AlibabaError as e:
        _error(e)


def render(products: list[dict], prod_names: dict) -> None:
    _handle_alibaba_callback()
    st.subheader("Connections")
    st.caption("Live data from your Amazon seller account and your Alibaba.com buyer account. "
               "Anything that changes Amazon or Alibaba asks you to confirm first; payments "
               "always open on Alibaba/PayPal for you to complete.")
    amazon_ok, alibaba_ok = AmazonClient.configured(), AlibabaClient.configured()
    token = factory.alibaba_token_info()
    c1, c2 = st.columns(2)
    c1.metric("Amazon Seller (SP-API)", "Connected" if amazon_ok else "Not set up")
    c2.metric("Alibaba.com (Open Platform)",
              "Authorized" if token else ("App set up, not authorized" if alibaba_ok else "Not set up"))

    amazon_tab, alibaba_tab = st.tabs(["Amazon", "Alibaba"])
    with amazon_tab:
        _amazon(products, prod_names, amazon_ok)
    with alibaba_tab:
        _alibaba(alibaba_ok, token)


def _amazon(products, prod_names, ok: bool) -> None:
    if not ok:
        st.info("Amazon is not connected yet.")
        st.markdown(AMAZON_SETUP)
        return
    try:
        client = factory.amazon()
    except AmazonError as e:
        _error(e)
        return

    a, b = st.columns(2)
    if a.button("Test connection"):
        try:
            parts = client.marketplace_participations()
            names = [p.get("marketplace", {}).get("name") for p in parts]
            st.success(f"Connected. Marketplaces: {', '.join(n for n in names if n)}")
        except AmazonError as e:
            _error(e)
    if b.button("Update fees from Amazon",
                help="Uses Amazon's fee estimate for each product that has an ASIN in Margins & prices"):
        try:
            res = sync.sync_amazon_fees(client)
            st.success(f"Updated {len(res['updated'])} product(s).")
            if res["skipped_no_asin"]:
                st.caption("No ASIN yet: " + ", ".join(res["skipped_no_asin"]))
        except AmazonError as e:
            _error(e)

    st.markdown("**Recent orders**")
    days = st.slider("Days", 1, 30, 7, key="amz_days")
    if st.button("Load orders"):
        try:
            after = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%SZ")
            rows = [{"Order": o.get("AmazonOrderId"), "Date": o.get("PurchaseDate"),
                     "Status": o.get("OrderStatus"), "Channel": o.get("FulfillmentChannel"),
                     "Items": o.get("NumberOfItemsShipped", 0) + o.get("NumberOfItemsUnshipped", 0),
                     "Total": (o.get("OrderTotal") or {}).get("Amount")}
                    for o in client.orders(after)]
            st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")
            if not rows:
                st.caption("No orders in this period.")
        except AmazonError as e:
            _error(e)

    st.markdown("**FBA inventory**")
    if st.button("Load inventory"):
        try:
            rows = [{"SKU": i.get("sellerSku"), "ASIN": i.get("asin"), "Name": i.get("productName"),
                     "Available": (i.get("inventoryDetails") or {}).get("fulfillableQuantity"),
                     "Inbound": sum((i.get("inventoryDetails") or {}).get(k, 0) or 0 for k in
                                    ("inboundWorkingQuantity", "inboundShippedQuantity",
                                     "inboundReceivingQuantity")),
                     "Total": i.get("totalQuantity")} for i in client.fba_inventory()]
            st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")
        except AmazonError as e:
            _error(e)

    st.markdown("**Change a price on Amazon**")
    with_sku = [p for p in products if p.get("sku")]
    if not with_sku:
        st.caption("Add your SKUs in Margins & prices to change prices from here.")
        return
    with st.form("amz_price"):
        pid = st.selectbox("Product", [p["id"] for p in with_sku], format_func=prod_names.get)
        p = next(x for x in with_sku if x["id"] == pid)
        price = st.number_input("New price £ (incl. VAT)", 0.5, 1000.0, float(p["sale_price"]), 0.1)
        ptype = st.text_input("Amazon product type", "PRODUCT",
                              help="As shown on the listing, e.g. PHONE_ACCESSORY")
        sure = st.checkbox(f"I approve changing {p['sku']} on Amazon to £{price:.2f}")
        if st.form_submit_button("Update price on Amazon", type="primary"):
            if not sure:
                st.warning("Tick the approval box first.")
            else:
                try:
                    res = client.update_price(p["sku"], price, ptype)
                    db.update("products", int(pid), {"sale_price": price})
                    st.success(f"Amazon answered: {res.get('status', 'OK')}")
                    if res.get("issues"):
                        st.json(res["issues"])
                except AmazonError as e:
                    _error(e)


def _alibaba(ok: bool, token: dict) -> None:
    if not ok:
        st.info("Alibaba is not connected yet.")
        st.markdown(ALIBABA_SETUP)
        return
    try:
        client = factory.alibaba()
    except AlibabaError as e:
        _error(e)
        return

    if token:
        st.success(f"Authorized as {token.get('user_nick') or token.get('account') or 'buyer'}")
        if st.button("Refresh access token"):
            try:
                client.refresh()
                st.success("Token refreshed.")
            except AlibabaError as e:
                _error(e)
    else:
        import secrets
        if "ali_state" not in st.session_state:
            st.session_state.ali_state = secrets.token_urlsafe(16)
            db.set_secret("alibaba_oauth_state", st.session_state.ali_state)
        st.link_button("Connect my Alibaba buyer account ↗",
                       client.authorize_url(st.session_state.ali_state))
        st.caption("You sign in on Alibaba and come back here automatically.")
        return

    st.markdown("**Search Alibaba**")
    with st.form("ali_search"):
        c1, c2, c3 = st.columns([3, 1, 1])
        kw = c1.text_input("Keywords", placeholder="e.g. silicone cable organiser")
        ship_to = c2.text_input("Ship to", "GB")
        page = c3.number_input("Page", 1, 100, 1)
        go_search = st.form_submit_button("Search")
    if go_search and kw:
        try:
            st.session_state.ali_results = client.search(kw, page=int(page), ship_to=ship_to)["products"]
        except AlibabaError as e:
            _error(e)
    results = st.session_state.get("ali_results") or []
    if results:
        rows = [{"Add": False, "ID": str(r.get("product_id")), "Title": r.get("title"),
                 "Price": r.get("price"), "Image": (r.get("image") or {}).get("main_image"),
                 "Link": r.get("permalink")} for r in results]
        picked = st.data_editor(
            pd.DataFrame(rows), hide_index=True, width="stretch", disabled=["ID", "Title", "Price"],
            column_config={"Add": st.column_config.CheckboxColumn("Add", width="small"),
                           "Image": st.column_config.ImageColumn("Image"),
                           "Link": st.column_config.LinkColumn("Link", display_text="Open ↗")},
            key="ali_pick")
        target = st.selectbox("Add ticked products as suppliers for", list(prod_names),
                              format_func=prod_names.get, key="ali_target")
        if st.button("Add to Suppliers"):
            chosen = picked[picked["Add"]]
            for _, r in chosen.iterrows():
                db.insert("suppliers", {
                    "product_id": target, "name": (r["Title"] or "")[:120], "url": r["Link"],
                    "status": "To contact", "unit_price_usd": first_price(r["Price"]),
                    "trade_assurance": 1, "notes": f"Alibaba product {r['ID']}"})
            st.success(f"Added {len(chosen)} supplier(s). See the Suppliers tab.")

    st.markdown("**Look up an Alibaba product**")
    with st.form("ali_product"):
        product_id = st.text_input("Alibaba product ID", help="The number in the product page URL")
        country = st.text_input("Ship-to country", "GB")
        go = st.form_submit_button("Look up")
    if go and product_id:
        try:
            res = client.product(product_id.strip(), country)
            st.json(res)
            inv = client.inventory(product_id.strip(), ship_to=country)
            with st.expander("Inventory"):
                st.json(inv)
        except AlibabaError as e:
            _error(e)

    st.markdown("**Track an Alibaba order**")
    with st.form("ali_order"):
        order_id = st.text_input("Alibaba order ID")
        go2 = st.form_submit_button("Get order and tracking")
    if go2 and order_id:
        try:
            st.json(client.order(order_id.strip()))
            st.json(client.tracking(order_id.strip()))
        except AlibabaError as e:
            _error(e)

    st.markdown("**Get a payment link** (PayPal)")
    with st.form("ali_pay"):
        ids = st.text_input("Order ID(s), comma separated")
        sure = st.checkbox("I approve requesting a payment link for these orders")
        go3 = st.form_submit_button("Get payment link")
    if go3 and ids:
        if not sure:
            st.warning("Tick the approval box first.")
        else:
            try:
                res = client.payment_link([i.strip() for i in ids.split(",") if i.strip()])
                st.json(res)
                st.caption("Open the PayPal link above to pay. Nothing has been charged yet.")
            except AlibabaError as e:
                _error(e)

    st.markdown("**Events received from Alibaba** (price changes, order status)")
    ev = db.events()
    if ev.empty:
        st.caption("None yet. Events arrive through the REST API's /alibaba/webhook.")
    else:
        st.dataframe(ev, hide_index=True, width="stretch")
