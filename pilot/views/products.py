"""Products & margins: each product's figures and the profit per unit."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from .. import calc, db, ui

PCT_COLS = ["duty_pct", "referral_pct", "ads_pct"]


def render() -> None:
    ctx = ui.load()
    st.title("📊 Products & margins")
    st.caption(f"Edit any number, then **Save**. Percentages are in %. Supplier cost is in USD "
               f"(converted at ${ctx.fx:.2f} = £1). Fees are per unit in £.")
    pdf = db.read("products")
    pdf[PCT_COLS] = pdf[PCT_COLS] * 100
    with st.form(f"products_{ui.ver()}"):
        edited = st.data_editor(
            pdf, num_rows="dynamic", hide_index=True, width="stretch",
            column_order=["name", "pack", "sale_price", "unit_cost_usd", "freight_per_unit", "duty_pct",
                          "referral_pct", "fba_fee", "ads_pct", "other_per_unit", "first_order_qty",
                          "first_order_fixed", "asin", "sku", "notes"],
            column_config={
                "name": st.column_config.TextColumn("Product", required=True),
                "pack": "Pack",
                "sale_price": st.column_config.NumberColumn("Price £", format="%.2f", min_value=0),
                "unit_cost_usd": st.column_config.NumberColumn("Supplier $/unit", format="%.2f"),
                "freight_per_unit": st.column_config.NumberColumn("Freight £/unit", format="%.2f"),
                "duty_pct": st.column_config.NumberColumn("Duty %", format="%.1f"),
                "referral_pct": st.column_config.NumberColumn("Referral %", format="%.1f"),
                "fba_fee": st.column_config.NumberColumn("FBA fee £", format="%.2f"),
                "ads_pct": st.column_config.NumberColumn("Ads % of price", format="%.1f"),
                "other_per_unit": st.column_config.NumberColumn("Other £/unit", format="%.2f",
                                                                help="Storage, returns, packaging"),
                "first_order_qty": st.column_config.NumberColumn("1st order qty", format="%d"),
                "first_order_fixed": st.column_config.NumberColumn(
                    "1st order fixed £", format="%.2f", help="Samples, inspection, labels"),
                "asin": "ASIN", "sku": "SKU", "notes": "Notes",
            })
        if st.form_submit_button("Save", type="primary"):
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
    money = {c: st.column_config.NumberColumn(c, format="£%.2f") for c in
             ["Price", "VAT", "Referral", "FBA", "Landed cost", "Ads", "Other", "Profit/unit",
              "1st order £"]}
    pct = {c: st.column_config.NumberColumn(c, format="%.1f%%") for c in ["Margin %", "ROI %", "Break-even ACoS %"]}
    st.markdown("**Results per unit sold**")
    st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch", column_config={**money, **pct})
    st.caption("Break-even ACoS: the share of the price advertising can cost before a sale loses money.")

    if not ctx.products:
        return
    st.markdown("**What if I changed the price?**")
    a, b = st.columns([1, 2])
    names = ctx.prod_names
    pid = a.selectbox("Product", list(names), format_func=names.get, key="whatif")
    p = ctx.prod_by_id[pid]
    new_price = a.slider("Sale price £", 1.0, max(50.0, p["sale_price"] * 2), float(p["sale_price"]), 0.5)
    target = a.slider("Target margin %", 5, 40, 20)
    e = calc.unit_economics({**p, "sale_price": new_price}, ctx.settings)
    a.metric("Profit per unit", ui.gbp(e.profit), f"{e.margin * 100:.1f}% margin · {e.band}")
    a.caption(f"Price needed for a {target}% margin: "
              f"**{ui.gbp(calc.price_for_margin(p, ctx.settings, target / 100))}**")
    breakdown = pd.DataFrame({"£": [e.vat, e.referral_fee, e.fba_fee, e.landed_cost, e.ads, e.other,
                                    max(e.profit, 0)]},
                             index=["VAT", "Referral fee", "FBA fee", "Landed cost", "Ads",
                                    "Other", "Profit"])
    b.markdown(f"Where the {ui.gbp(new_price)} goes")
    b.bar_chart(breakdown, horizontal=True)
