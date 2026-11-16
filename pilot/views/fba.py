"""Stock & FBA shipments: your stock in Amazon's warehouses."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from .. import ui
from ..connections import show_error
from ..integrations import AmazonClient, AmazonError, factory


def render() -> None:
    ctx = ui.load()
    st.title("🚚 Stock & FBA shipments")
    st.caption("With FBA, Amazon stores your products and delivers every order itself, so your goods "
               "must be sent to its warehouses before you can sell.")
    st.info("Coming in part 2: create the shipment to Amazon's warehouses and print the labels from this "
            "page. Until then: Seller Central → Inventory → Send to Amazon.")
    en_route = ctx.orders[ctx.orders["status"].isin(["Paid", "In production", "Shipped"])]
    st.subheader("Goods on their way from suppliers")
    if en_route.empty:
        st.caption("No supplier orders in progress.")
    else:
        st.dataframe(pd.DataFrame({
            "Product": en_route["product_id"].map(ctx.prod_names), "Quantity": en_route["qty"],
            "Status": en_route["status"], "Tracking": en_route["tracking"], "ETA": en_route["eta"]}),
            hide_index=True, width="stretch")
        ui.link("Purchases & payments", "Track orders →", "🧾")

    st.subheader("Stock at Amazon")
    if not AmazonClient.configured():
        st.caption("Connect Amazon (Connections page) to see your stock.")
        return
    if st.button("Load FBA stock"):
        try:
            rows = [{"SKU": i.get("sellerSku"), "ASIN": i.get("asin"), "Product": i.get("productName"),
                     "Available": (i.get("inventoryDetails") or {}).get("fulfillableQuantity"),
                     "Inbound": sum((i.get("inventoryDetails") or {}).get(k, 0) or 0 for k in
                                    ("inboundWorkingQuantity", "inboundShippedQuantity",
                                     "inboundReceivingQuantity")),
                     "Total": i.get("totalQuantity")} for i in factory.amazon().fba_inventory()]
            st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")
            if not rows:
                st.caption("No stock at Amazon yet.")
        except AmazonError as e:
            show_error(e)
