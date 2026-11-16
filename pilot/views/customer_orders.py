"""Amazon customer orders. With FBA, Amazon picks, packs and delivers: nothing to approve."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pandas as pd
import streamlit as st

from .. import ui
from ..connections import show_error
from ..integrations import AmazonClient, AmazonError, factory
from ..i18n import t, table


def render() -> None:
    ui.load()
    st.title(t("🛒 Customer orders"))
    st.caption(t("Your sales on Amazon. **With FBA there is nothing to approve**: as soon as a customer "
               "pays, Amazon packs the parcel in its warehouse and delivers it. The money then reaches "
               "your bank account (see Cash)."))
    if not AmazonClient.configured():
        st.info(t("Connect Amazon (Connections page) to see your orders."))
        return
    days = st.slider(t("Period (days)"), 1, 30, 7)
    if st.button(t("Load orders"), type="primary"):
        try:
            after = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%SZ")
            rows = [{"Order": o.get("AmazonOrderId"),
                     "Date": (o.get("PurchaseDate") or "")[:16].replace("T", " "),
                     "Status": o.get("OrderStatus"),
                     "Fulfilled by": "Amazon (FBA)" if o.get("FulfillmentChannel") == "AFN" else t("You (FBM)"),
                     "Items": (o.get("NumberOfItemsShipped") or 0) + (o.get("NumberOfItemsUnshipped") or 0),
                     "Total £": float((o.get("OrderTotal") or {}).get("Amount") or 0)}
                    for o in factory.amazon().orders(after)]
            if rows:
                df = pd.DataFrame(rows)
                m1, m2 = st.columns(2)
                m1.metric(t("Orders"), len(df))
                m2.metric(t("Sales"), ui.gbp(df["Total £"].sum()))
                table(df, {"Total £": st.column_config.NumberColumn(format="£%.2f")})
            else:
                st.caption(t("No orders in this period."))
        except AmazonError as e:
            show_error(e)
