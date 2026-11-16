"""Dashboard: where each product stands, what to do next, how much money is committed."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from .. import pipeline, ui


def render() -> None:
    ctx = ui.load()
    st.title("Dashboard")
    st.caption("Each product's journey, from searching on Alibaba to selling on Amazon. Nothing is "
               "sent to a supplier or changed on Amazon without your approval.")

    stages = {p["id"]: ctx.stage(p["id"]) for p in ctx.products}
    counts = pd.Series(list(stages.values()), dtype=object).value_counts()
    st.subheader("The journey")
    cols = st.columns(len(pipeline.STAGES))
    for col, name in zip(cols, pipeline.STAGES):
        col.metric(name, int(counts.get(name, 0)))

    st.subheader("To do now")
    if not ctx.products:
        st.info("No products yet. Start by searching for a product.")
        ui.link("Product search", "Search for a product →", "🔎")
    for p in ctx.products:
        action, page = ctx.next_action(p["id"])
        c1, c2 = st.columns([3, 1])
        c1.markdown(f"**{p['name']}** {ui.stage_badge(stages[p['id']])}  \n{action}", unsafe_allow_html=True)
        with c2:
            ui.link(page, f"{page} →")

    st.subheader("Money")
    orders = ctx.orders
    active = orders[orders["status"] != "Cancelled"] if not orders.empty else orders
    total = sum(ctx.order_total_gbp(r) for _, r in active.iterrows())
    paid = float(active["paid_gbp"].fillna(0).sum()) if not active.empty else 0.0
    m1, m2, m3 = st.columns(3)
    m1.metric("Supplier purchases", ui.gbp(total))
    m2.metric("Paid", ui.gbp(paid))
    m3.metric("Left to pay", ui.gbp(total - paid))
    ui.link("Cash", "Open Cash →", "💷")

    st.subheader("Your products")
    st.caption("Starting figures you can change in Products & margins.")
    cols = st.columns(2)
    for i, p in enumerate(ctx.products):
        e = ctx.econ[p["id"]]
        with cols[i % 2].container(border=True):
            st.markdown(f"**{p['name']}** {ui.stage_badge(stages[p['id']])}  \n"
                        f"<span class='sub'>{p['pack']} · selling at {ui.gbp(p['sale_price'])}</span>",
                        unsafe_allow_html=True)
            st.markdown(f"<div class='big'>{ui.gbp(e.profit)}</div>{ui.badge(e.band, e.margin)}"
                        f"<span class='sub'>per unit sold</span>", unsafe_allow_html=True)
            st.markdown(f"<span class='sub'>First order of {p['first_order_qty']} units: about "
                        f"{ui.gbp(e.first_order_cash)} to pay upfront.</span>", unsafe_allow_html=True)

    cl = ctx.checklist
    done, total_steps = int(cl["done"].fillna(0).sum()), len(cl)
    todo = cl[cl["done"].fillna(0) == 0]
    with st.container(border=True):
        st.markdown(f"**Getting started: {done / total_steps * 100 if total_steps else 0:.0f} %** "
                    f"({done} of {total_steps} steps)")
        st.progress(done / total_steps if total_steps else 0.0)
        if not todo.empty:
            st.caption(f"Next step: {todo.iloc[0]['step']}")
