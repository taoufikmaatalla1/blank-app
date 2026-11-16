"""Amazon competition: log competing listings and see where your price sits."""

from __future__ import annotations

from urllib.parse import quote_plus

import pandas as pd
import streamlit as st

from .. import db, ui


def render() -> None:
    ctx = ui.load()
    st.title("🆚 Amazon competition")
    if not ctx.products:
        st.info("Add a product first.")
        return
    names = ctx.prod_names
    pid = st.selectbox("Product", list(names), format_func=names.get, key="cmp")
    p = ctx.prod_by_id[pid]
    q = quote_plus(f"{p['name']} {p['pack']}".replace("Christmas:", ""))
    st.link_button("Search amazon.co.uk ↗", f"https://www.amazon.co.uk/s?k={q}")
    comp = db.read("competitors")
    mine = comp[comp["product_id"] == pid].drop(columns=["product_id"])
    with st.form(f"comp_{pid}_{ui.ver()}"):
        st.caption("Note the top competing listings: price, rating, reviews, Best Sellers Rank.")
        ed = st.data_editor(
            mine, num_rows="dynamic", hide_index=True, width="stretch",
            column_order=["asin", "title", "price", "rating", "reviews", "bsr", "monthly_sales_est", "notes"],
            column_config={
                "asin": "ASIN", "title": "Title",
                "price": st.column_config.NumberColumn("Prix £", format="%.2f"),
                "rating": st.column_config.NumberColumn("Rating", min_value=0, max_value=5, format="%.1f"),
                "reviews": st.column_config.NumberColumn("Reviews", format="%d"),
                "bsr": st.column_config.NumberColumn("BSR", format="%d"),
                "monthly_sales_est": st.column_config.NumberColumn("Est. sales/month", format="%d"),
                "notes": "Notes",
            })
        if st.form_submit_button("Save", type="primary"):
            ed["product_id"] = pid
            db.write("competitors", pd.concat([comp[comp["product_id"] != pid], ed]))
            ui.bump()
            st.rerun()
    if not mine.empty and mine["price"].notna().any():
        avg = mine["price"].mean()
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Your price", ui.gbp(p["sale_price"]),
                  f"{(p['sale_price'] / avg - 1) * 100:+.0f}% vs average", delta_color="inverse")
        m2.metric("Competitor average", ui.gbp(avg))
        m3.metric("Lowest / highest", f"{ui.gbp(mine['price'].min())} / {ui.gbp(mine['price'].max())}")
        m4.metric("Median reviews", f"{mine['reviews'].median():,.0f}" if mine["reviews"].notna().any() else "–")
        chart = mine.dropna(subset=["price"]).assign(
            label=lambda d: d["asin"].fillna("").where(d["asin"].fillna("") != "", d["title"]))
        chart = pd.concat([chart[["label", "price"]], pd.DataFrame([{"label": "★ You", "price": p["sale_price"]}])])
        st.bar_chart(chart.set_index("label"))
