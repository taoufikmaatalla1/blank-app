"""Cash: what you paid suppliers, what is left to pay, what Amazon pays you."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from .. import ui
from ..i18n import t, table


def render() -> None:
    ctx = ui.load()
    st.title(t("💷 Cash"))
    orders = ctx.orders
    active = orders[orders["status"] != "Cancelled"].copy() if not orders.empty else orders
    st.subheader(t("Supplier purchases"))
    if active.empty:
        st.caption(t("No purchase orders yet."))
    else:
        active["Total £"] = active.apply(ctx.order_total_gbp, axis=1)
        active["Paid £"] = active["paid_gbp"].fillna(0)
        active["Left £"] = active["Total £"] - active["Paid £"]
        m1, m2, m3 = st.columns(3)
        m1.metric(t("Total purchases"), ui.gbp(active["Total £"].sum()))
        m2.metric(t("Paid"), ui.gbp(active["Paid £"].sum()))
        m3.metric(t("Left to pay"), ui.gbp(active["Left £"].sum()))
        by_prod = (active.assign(Product=active["product_id"].map(ctx.prod_names))
                   .groupby("Product")[["Total £", "Paid £", "Left £"]].sum().reset_index())
        table(by_prod, {
            c: st.column_config.NumberColumn(format="£%.2f") for c in ("Total £", "Paid £", "Left £")})
        due = active[active["Left £"] > 0.01]
        if not due.empty:
            st.markdown(t("**To pay**"))
            table(pd.DataFrame({
                "Order": due["id"].map(lambda i: f"#{int(i)}"),
                "Product": due["product_id"].map(ctx.prod_names), "Left £": due["Left £"],
                "Payment": due["payment_method"], "Status": due["status"]}),
                {"Left £": st.column_config.NumberColumn(format="£%.2f")}, status_cols=["Status"])
            ui.link("Purchases & payments", t("Pay an order →"), "🧾")

    st.subheader(t("Amazon payouts"))
    st.info(t("Coming in part 3: your sales, the fees Amazon keeps, and the payouts to your bank account "
            "(Amazon pays about every 2 weeks). This needs the **Finance and Accounting** role on your "
            "Amazon developer profile."))
