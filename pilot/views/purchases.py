"""Step 3: order from the chosen supplier, pay, and follow the order until it reaches Amazon."""

from __future__ import annotations

import json
from datetime import date

import pandas as pd
import streamlit as st

from .. import db, ui
from ..connections import alibaba_ready, show_error
from ..integrations import AlibabaError, factory

ALIBABA_ORDERS_URL = "https://biz.alibaba.com/order/list.htm?role=buyer"


def map_alibaba_status(raw: str | None) -> str | None:
    """Translate an Alibaba order status into this app's order status."""
    s = (raw or "").lower()
    if not s:
        return None
    if "close" in s or "cancel" in s:
        return "Cancelled"
    if "unpay" in s or "wait_buyer_pay" in s or "wait_pay" in s:
        return "Awaiting payment"
    if "receive" in s or "ship" in s or "send_goods" in s or "deliver" in s or "success" in s \
            or "finish" in s:
        return "Shipped" if "wait_seller" not in s else "Paid"
    if "paid" in s or "wait_seller" in s or "pay_success" in s or "produc" in s:
        return "Paid"
    return None


def find_url(obj) -> str | None:
    """First http(s) link found in a JSON response (the PayPal payment link)."""
    if isinstance(obj, str):
        return obj if obj.startswith("http") else None
    if isinstance(obj, dict):
        obj = list(obj.values())
    if isinstance(obj, list):
        for v in obj:
            u = find_url(v)
            if u:
                return u
    return None


def render() -> None:
    ctx = ui.load()
    st.title("🧾 Purchases & payments")
    st.caption("Create the order with the chosen supplier, pay it (Trade Assurance or Alibaba PayPal "
               "link) and follow it until it reaches Amazon. The app never pays for you: it opens the "
               "payment page and records what has been paid.")
    names, sups = ctx.prod_names, ctx.suppliers
    sup_names = dict(zip(sups["id"], sups["name"]))
    orders = ctx.orders

    # ------------------------------------------------------------ totaux
    active = orders[orders["status"] != "Cancelled"] if not orders.empty else orders
    total = sum(ctx.order_total_gbp(r) for _, r in active.iterrows())
    paid = float(active["paid_gbp"].fillna(0).sum()) if not active.empty else 0.0
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total ordered", ui.gbp(total))
    m2.metric("Paid", ui.gbp(paid))
    m3.metric("Left to pay", ui.gbp(total - paid))
    m4.metric("Open orders", len(active[~active["status"].isin(["At Amazon FC"])])
              if not active.empty else 0)

    # ------------------------------------------------------------ nouvelle commande
    st.subheader("New purchase order")
    retained = sups[sups["status"] == "Selected"]
    if sups.empty:
        st.info("No suppliers yet. Start with Product search.")
    else:
        default_sid = int(retained.iloc[0]["id"]) if not retained.empty else int(sups.iloc[0]["id"])
        options = sups["id"].tolist()
        sid = st.selectbox(
            "Supplier", options, index=options.index(default_sid),
            format_func=lambda i: f"{'⭐ ' if sups.set_index('id').loc[i, 'status'] == 'Selected' else ''}"
                                  f"{sup_names[i]} — {names.get(sups.set_index('id').loc[i, 'product_id'], '?')}")
        s = sups.set_index("id").loc[sid].to_dict()
        prod = ctx.prod_by_id.get(s["product_id"], {})
        with st.form(f"new_order_{sid}", clear_on_submit=True):
            c1, c2, c3 = st.columns(3)
            qty = c1.number_input("Quantity", 1, 1_000_000,
                                  int(s.get("moq") or prod.get("first_order_qty") or 100), 10)
            price = c2.number_input("Price $/unit", 0.0, 100000.0,
                                    float(s.get("unit_price_usd") or prod.get("unit_cost_usd") or 0), 0.01)
            ship = c3.number_input("Shipping $", 0.0, 1_000_000.0,
                                   float(s.get("shipping_usd") or 0) if pd.notna(s.get("shipping_usd")) else 0.0, 1.0)
            c4, c5 = st.columns(2)
            method = c4.selectbox("Payment", db.PAYMENT_METHODS)
            trade = c5.text_input("Alibaba order number (if already created)",
                                  help="The Trade Assurance order number, shown in My Orders on Alibaba.")
            notes = st.text_input("Notes")
            st.caption(f"Total: {ui.usd(qty * price + ship)} ≈ {ui.gbp((qty * price + ship) / ctx.fx)}")
            if st.form_submit_button("Create order", type="primary"):
                db.insert("orders", {
                    "product_id": s["product_id"], "supplier_id": int(sid),
                    "order_date": date.today().isoformat(), "qty": int(qty), "unit_price_usd": price,
                    "shipping_usd": ship, "status": "Awaiting payment", "paid_gbp": 0.0,
                    "payment_method": method, "alibaba_trade_id": trade.strip(), "notes": notes})
                ui.bump()
                ui.flash("Order created. Pay it, then record the payment below.")
                st.rerun()
        st.link_button("My orders on Alibaba ↗", ALIBABA_ORDERS_URL)

    if orders.empty:
        return

    # ------------------------------------------------------------ une commande
    st.subheader("Pay and track an order")
    labels = {int(r["id"]): f"#{int(r['id'])} · {names.get(r['product_id'], '?')} · "
                            f"{ui.gbp(ctx.order_total_gbp(r))} · {r['status']}"
              for _, r in orders.iterrows()}
    unpaid = [i for i, r in orders.set_index("id").iterrows()
              if r["status"] in ("Draft", "Awaiting payment")]
    oid = st.selectbox("Order", list(labels), format_func=labels.get,
                       index=list(labels).index(unpaid[0]) if unpaid else 0)
    o = orders.set_index("id").loc[oid].to_dict()
    o_total = ctx.order_total_gbp(o)
    o_paid = float(o.get("paid_gbp") or 0) if pd.notna(o.get("paid_gbp")) else 0.0
    c1, c2, c3 = st.columns(3)
    c1.metric("Amount", ui.gbp(o_total))
    c2.metric("Paid", ui.gbp(o_paid))
    c3.metric("Status", o["status"])

    a, b = st.columns(2)
    with a:
        st.markdown("**Payment**")
        link = o.get("payment_link") if isinstance(o.get("payment_link"), str) else ""
        if link:
            st.link_button("Pay this order ↗", link, type="primary")
        trade = o.get("alibaba_trade_id") if isinstance(o.get("alibaba_trade_id"), str) else ""
        if trade and alibaba_ready():
            ok = st.checkbox("I approve requesting a PayPal payment link for this order",
                             key=f"pay_ok_{oid}")
            if st.button("Get the Alibaba payment link", disabled=not ok):
                try:
                    res = factory.alibaba().payment_link([trade])
                    url = find_url(res)
                    if url:
                        db.update("orders", int(oid), {"payment_link": url})
                        ui.bump()
                        ui.flash("Payment link ready: click \"Pay this order\".")
                        st.rerun()
                    st.json(res)
                except AlibabaError as e:
                    show_error(e)
        elif not trade:
            st.caption("Pay on Alibaba (Trade Assurance), then record the payment here. Add the "
                       "Alibaba order number in the table below to track the order automatically.")
        with st.form(f"paid_{oid}"):
            amount = st.number_input("Amount paid £", 0.0, 1_000_000.0,
                                     round(max(o_total - o_paid, 0.0), 2), 1.0)
            when = st.date_input("Payment date", date.today())
            if st.form_submit_button("Record this payment"):
                new_paid = o_paid + amount
                vals = {"paid_gbp": round(new_paid, 2), "paid_date": when.isoformat()}
                if new_paid >= o_total - 0.01 and o["status"] in ("Draft", "Awaiting payment"):
                    vals["status"] = "Paid"
                db.update("orders", int(oid), vals)
                ui.bump()
                ui.flash("Payment recorded.")
                st.rerun()
    with b:
        st.markdown("**Tracking**")
        if trade and alibaba_ready():
            if st.button("Refresh from Alibaba"):
                try:
                    client = factory.alibaba()
                    detail = client.order(trade).get("value") or {}
                    raw = detail.get("trade_status") or (detail.get("status_action") or {}).get("status")
                    vals = {"alibaba_status": raw}
                    mapped = map_alibaba_status(raw)
                    if mapped and o["status"] != "At Amazon FC":
                        vals["status"] = mapped
                    for act in (detail.get("status_action") or {}).get("actions") or []:
                        if act.get("name") == "view_payment_link" and act.get("value"):
                            vals["payment_link"] = act["value"]
                    try:
                        track = client.tracking(trade)
                        vals["tracking"] = json.dumps(track.get("value") or track.get("result") or track,
                                                      ensure_ascii=False)[:500]
                    except AlibabaError:
                        pass
                    db.update("orders", int(oid), vals)
                    ui.bump()
                    ui.flash(f"Order refreshed (Alibaba status: {raw or 'unknown'}).")
                    st.rerun()
                except AlibabaError as e:
                    show_error(e)
        elif trade:
            st.caption("Connect Alibaba (Connections page) to refresh the status automatically.")
        st.write(f"Alibaba status: {o.get('alibaba_status') or '–'}")
        st.write(f"Tracking: {o.get('tracking') or '–'}")
        new_status = st.selectbox("Change status", db.ORDER_STATUSES,
                                  index=db.ORDER_STATUSES.index(o["status"]) if o["status"] in db.ORDER_STATUSES else 0,
                                  key=f"st_{oid}_{ui.ver()}")
        if new_status != o["status"] and st.button("Save status"):
            db.update("orders", int(oid), {"status": new_status})
            ui.bump()
            st.rerun()

    # ------------------------------------------------------------ toutes les commandes
    st.subheader("All orders")
    odf = orders.copy()
    odf["product"] = odf["product_id"].map(names)
    odf["supplier"] = odf["supplier_id"].map(sup_names)
    odf["total"] = odf.apply(ctx.order_total_gbp, axis=1)
    for c in ("order_date", "eta"):
        odf[c] = pd.to_datetime(odf[c], errors="coerce").dt.date
    with st.form(f"orders_{ui.ver()}"):
        ed = st.data_editor(
            odf, hide_index=True, width="stretch", num_rows="dynamic",
            column_order=["order_date", "product", "supplier", "qty", "unit_price_usd", "shipping_usd",
                          "total", "status", "paid_gbp", "payment_method", "alibaba_trade_id",
                          "tracking", "eta", "notes"],
            disabled=["total"],
            column_config={
                "order_date": st.column_config.DateColumn("Date"),
                "product": st.column_config.SelectboxColumn("Product", options=list(names.values()),
                                                            required=True),
                "supplier": st.column_config.SelectboxColumn("Supplier",
                                                             options=list(sup_names.values())),
                "qty": st.column_config.NumberColumn("Qty", format="%d", min_value=0),
                "unit_price_usd": st.column_config.NumberColumn("$/unit", format="%.2f"),
                "shipping_usd": st.column_config.NumberColumn("Shipping $", format="%.2f"),
                "total": st.column_config.NumberColumn("Total £", format="£%.2f"),
                "status": st.column_config.SelectboxColumn("Status", options=db.ORDER_STATUSES,
                                                           default="Draft", required=True),
                "paid_gbp": st.column_config.NumberColumn("Paid £", format="%.2f"),
                "payment_method": st.column_config.SelectboxColumn("Payment", options=db.PAYMENT_METHODS),
                "alibaba_trade_id": st.column_config.TextColumn("Alibaba order #"),
                "tracking": "Tracking", "eta": st.column_config.DateColumn("ETA"),
                "notes": "Notes",
            })
        if st.form_submit_button("Save"):
            ed["product_id"] = ed["product"].map({v: k for k, v in names.items()})
            ed["supplier_id"] = ed["supplier"].map({v: k for k, v in sup_names.items()})
            for c in ("order_date", "eta"):
                ed[c] = ed[c].astype(str).replace({"None": None, "NaT": None})
            db.write("orders", ed.drop(columns=["product", "supplier", "total"]))
            ui.bump()
            st.rerun()
