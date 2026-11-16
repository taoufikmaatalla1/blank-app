"""Products & margins: each product's figures and the profit per unit."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from .. import calc, db, ui
from ..i18n import t

PCT_COLS = ["duty_pct", "referral_pct", "ads_pct"]


def render() -> None:
    ctx = ui.load()
    st.title(t("📊 Products & margins"))
    st.caption(t("Edit any number, then **Save**. Percentages are in %. Supplier cost is in USD "
                 "(converted at ${fx:.2f} = £1). Fees are per unit in £.", fx=ctx.fx))
    pdf = db.read("products")
    pdf[PCT_COLS] = pdf[PCT_COLS] * 100
    with st.form(f"products_{ui.ver()}"):
        edited = st.data_editor(
            pdf, num_rows="dynamic", hide_index=True, width="stretch",
            column_order=["name", "pack", "sale_price", "unit_cost_usd", "freight_per_unit", "duty_pct",
                          "referral_pct", "fba_fee", "ads_pct", "other_per_unit", "first_order_qty",
                          "first_order_fixed", "asin", "sku", "notes"],
            column_config={
                "name": st.column_config.TextColumn(t("Product"), required=True),
                "pack": t("Pack"),
                "sale_price": st.column_config.NumberColumn(t("Price £"), format="%.2f", min_value=0),
                "unit_cost_usd": st.column_config.NumberColumn(t("Supplier $/unit"), format="%.2f"),
                "freight_per_unit": st.column_config.NumberColumn(t("Freight £/unit"), format="%.2f"),
                "duty_pct": st.column_config.NumberColumn(t("Duty %"), format="%.1f"),
                "referral_pct": st.column_config.NumberColumn(t("Referral %"), format="%.1f"),
                "fba_fee": st.column_config.NumberColumn(t("FBA fee £"), format="%.2f"),
                "ads_pct": st.column_config.NumberColumn(t("Ads % of price"), format="%.1f"),
                "other_per_unit": st.column_config.NumberColumn(t("Other £/unit"), format="%.2f",
                                                                help=t("Storage, returns, packaging")),
                "first_order_qty": st.column_config.NumberColumn(t("1st order qty"), format="%d"),
                "first_order_fixed": st.column_config.NumberColumn(
                    t("1st order fixed £"), format="%.2f", help=t("Samples, inspection, labels")),
                "asin": "ASIN", "sku": "SKU", "notes": t("Notes"),
            })
        if st.form_submit_button(t("Save"), type="primary"):
            edited[PCT_COLS] = edited[PCT_COLS] / 100
            db.write("products", edited)
            ui.bump()
            st.rerun()

    rows = []
    for p in ctx.products:
        e = ctx.econ[p["id"]]
        rows.append({"Product": p["name"], "Price": e.price, "VAT": e.vat, "Referral": e.referral_fee,
                     "FBA": e.fba_fee, "Landed cost": e.landed_cost, "Ads": e.ads, "Other": e.other,
                     "Profit/unit": e.profit, "Margin %": e.margin * 100, "ROI %": e.roi * 100,
                     "Break-even ACoS %": e.breakeven_acos * 100, "1st order £": e.first_order_cash,
                     "Verdict": e.band})
    money = {c: st.column_config.NumberColumn(t(c), format="£%.2f") for c in
             ["Price", "VAT", "Referral", "FBA", "Landed cost", "Ads", "Other", "Profit/unit",
              "1st order £"]}
    pct = {c: st.column_config.NumberColumn(t(c), format="%.1f%%") for c in ["Margin %", "ROI %", "Break-even ACoS %"]}
    st.markdown(t("**Results per unit sold**"))
    df = pd.DataFrame(rows)
    if not df.empty:
        df["Verdict"] = df["Verdict"].map(t)
    st.dataframe(df, hide_index=True, width="stretch",
                 column_config={**money, **pct, "Product": t("Product"), "Verdict": t("Verdict")})
    st.caption(t("Break-even ACoS: the share of the price advertising can cost before a sale loses money."))

    if not ctx.products:
        return
    st.markdown(t("**What if I changed the price?**"))
    a, b = st.columns([1, 2])
    names = ctx.prod_names
    pid = a.selectbox(t("Product"), list(names), format_func=names.get, key="whatif")
    p = ctx.prod_by_id[pid]
    new_price = a.slider(t("Sale price £"), 1.0, max(50.0, p["sale_price"] * 2), float(p["sale_price"]), 0.5)
    target = a.slider(t("Target margin %"), 5, 40, 20)
    e = calc.unit_economics({**p, "sale_price": new_price}, ctx.settings)
    a.metric(t("Profit per unit"), ui.gbp(e.profit), t("{m:.1f}% margin · {band}", m=e.margin * 100, band=t(e.band)))
    a.caption(t("Price needed for a {target}% margin: **{price}**", target=target,
                price=ui.gbp(calc.price_for_margin(p, ctx.settings, target / 100))))
    breakdown = pd.DataFrame({"£": [e.vat, e.referral_fee, e.fba_fee, e.landed_cost, e.ads, e.other,
                                    max(e.profit, 0)]},
                             index=[t(x) for x in ["VAT", "Referral fee", "FBA fee", "Landed cost",
                                                   "Ads", "Other", "Profit"]])
    b.markdown(t("Where the {price} goes", price=ui.gbp(new_price)))
    b.bar_chart(breakdown, horizontal=True)
