"""Cash: what you paid suppliers, what is left to pay, what Amazon pays you."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from .. import ui


def render() -> None:
    ctx = ui.load()
    st.title("💷 Cash")
    orders = ctx.orders
    active = orders[orders["status"] != "Cancelled"].copy() if not orders.empty else orders
    st.subheader("Supplier purchases")
    if active.empty:
        st.caption("No purchase orders yet.")
    else:
        active["Total £"] = active.apply(ctx.order_total_gbp, axis=1)
        active["Paid £"] = active["paid_gbp"].fillna(0)
        active["Left £"] = active["Total £"] - active["Paid £"]
        m1, m2, m3 = st.columns(3)
        m1.metric("Total purchases", ui.gbp(active["Total £"].sum()))
        m2.metric("Paid", ui.gbp(active["Paid £"].sum()))
        m3.metric("Left to pay", ui.gbp(active["Left £"].sum()))
        by_prod = (active.assign(Product=active["product_id"].map(ctx.prod_names))
                   .groupby("Product")[["Total £", "Paid £", "Left £"]].sum().reset_index())
        st.dataframe(by_prod, hide_index=True, width="stretch", column_config={
            c: st.column_config.NumberColumn(format="£%.2f") for c in ("Total £", "Paid £", "Left £")})
        due = active[active["Left £"] > 0.01]
        if not due.empty:
            st.markdown("**To pay**")
            st.dataframe(pd.DataFrame({
                "Order": due["id"].map(lambda i: f"#{int(i)}"),
                "Product": due["product_id"].map(ctx.prod_names), "Left £": due["Left £"],
                "Payment": due["payment_method"], "Status": due["status"]}),
                hide_index=True, width="stretch",
                column_config={"Left £": st.column_config.NumberColumn(format="£%.2f")})
            ui.link("Purchases & payments", "Pay an order →", "🧾")

    st.subheader("Amazon payouts")
    st.info("Coming in part 3: your sales, the fees Amazon keeps, and the payouts to your bank account "
            "(Amazon pays about every 2 weeks). This needs the **Finance and Accounting** role on your "
            "Amazon developer profile.")
