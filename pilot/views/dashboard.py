"""Dashboard: where each product stands, what to do next, how much money is committed."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from .. import pipeline, ui
from ..i18n import t


def render() -> None:
    ctx = ui.load()
    st.title(t("Dashboard"))
    st.caption(t("Each product's journey, from searching on Alibaba to selling on Amazon. Nothing is "
               "sent to a supplier or changed on Amazon without your approval."))

    stages = {p["id"]: ctx.stage(p["id"]) for p in ctx.products}
    counts = pd.Series(list(stages.values()), dtype=object).value_counts()
    st.subheader(t("The journey"))
    cols = st.columns(len(pipeline.STAGES))
    for col, name in zip(cols, pipeline.STAGES):
        col.metric(t(name), int(counts.get(name, 0)))

    st.subheader(t("To do now"))
    if not ctx.products:
        st.info(t("No products yet. Start by searching for a product."))
        ui.link("Product search", t("Search for a product →"), "🔎")
    for p in ctx.products:
        action, page = ctx.next_action(p["id"])
        c1, c2 = st.columns([3, 1])
        c1.markdown(f"**{p['name']}** {ui.stage_badge(stages[p['id']])}  \n{t(action)}", unsafe_allow_html=True)
        with c2:
            ui.link(page, f"{t(page)} →")

    st.subheader(t("Money"))
    orders = ctx.orders
    active = orders[orders["status"] != "Cancelled"] if not orders.empty else orders
    total = sum(ctx.order_total_gbp(r) for _, r in active.iterrows())
    paid = float(active["paid_gbp"].fillna(0).sum()) if not active.empty else 0.0
    m1, m2, m3 = st.columns(3)
    m1.metric(t("Supplier purchases"), ui.gbp(total))
    m2.metric(t("Paid"), ui.gbp(paid))
    m3.metric(t("Left to pay"), ui.gbp(total - paid))
    ui.link("Cash", t("Open Cash →"), "💷")

    st.subheader(t("Your products"))
    st.caption(t("Starting figures you can change in Products & margins."))
    cols = st.columns(2)
    for i, p in enumerate(ctx.products):
        e = ctx.econ[p["id"]]
        with cols[i % 2].container(border=True):
            st.markdown(f"**{p['name']}** {ui.stage_badge(stages[p['id']])}  \n"
                        f"<span class='sub'>{p['pack']} · {t('selling at')} {ui.gbp(p['sale_price'])}</span>",
                        unsafe_allow_html=True)
            st.markdown(f"<div class='big'>{ui.gbp(e.profit)}</div>{ui.badge(e.band, e.margin)}"
                        f"<span class='sub'>{t('per unit sold')}</span>", unsafe_allow_html=True)
            st.markdown("<span class='sub'>" + t("First order of {qty} units: about {cash} to pay upfront.",
                                                   qty=p["first_order_qty"], cash=ui.gbp(e.first_order_cash))
                        + "</span>", unsafe_allow_html=True)

    cl = ctx.checklist
    done, total_steps = int(cl["done"].fillna(0).sum()), len(cl)
    todo = cl[cl["done"].fillna(0) == 0]
    with st.container(border=True):
        st.markdown(t("**Getting started: {pct:.0f} %** ({done} of {total} steps)",
                      pct=done / total_steps * 100 if total_steps else 0, done=done, total=total_steps))
        st.progress(done / total_steps if total_steps else 0.0)
        if not todo.empty:
            st.caption(t("Next step: {step}", step=todo.iloc[0]["step"]))
