"""Seller control center: manage Amazon UK selling and Alibaba sourcing in one place."""

from __future__ import annotations

import json
from urllib.parse import quote_plus

import pandas as pd
import streamlit as st

from pilot import calc, connections, db, messages

st.set_page_config(page_title="Seller Control Center", page_icon="📦", layout="wide")

st.markdown(
    """
<style>
.eyebrow {font-family: ui-monospace, Menlo, monospace; font-size: .75rem; letter-spacing: .06em;
          text-transform: uppercase; opacity: .7;}
.eyebrow b {opacity: 1;}
.big {font-family: ui-monospace, Menlo, monospace; font-size: 2rem; font-weight: 600; line-height: 1.1;}
.sub {font-size: .85rem; opacity: .75;}
.badge {font-family: ui-monospace, Menlo, monospace; font-size: .75rem; padding: 2px 8px;
        border-radius: 4px; margin-right: 8px;}
.b-Solid {background: rgba(46,160,67,.15); color: #2ea043;}
.b-Thin {background: rgba(210,153,34,.15); color: #b7791f;}
.b-Too {background: rgba(218,54,51,.15); color: #da3633;}
</style>
""",
    unsafe_allow_html=True,
)

db.init()
settings = db.get_settings()
FX = float(settings["usd_per_gbp"])

if "ver" not in st.session_state:
    st.session_state.ver = 0


def bump() -> None:
    """Force data editors to re-read from the database after a save."""
    st.session_state.ver += 1


def gbp(x: float) -> str:
    return f"£{x:,.2f}"


def badge(band: str, margin: float) -> str:
    cls = band.split()[0]
    return f'<span class="badge b-{cls}">{band} · {margin * 100:.1f} %</span>'


products = db.records("products")
prod_by_id = {p["id"]: p for p in products}
prod_names = {p["id"]: p["name"] for p in products}
name_to_pid = {v: k for k, v in prod_names.items()}
econ = {p["id"]: calc.unit_economics(p, settings) for p in products}

# ---------------------------------------------------------------- sidebar
with st.sidebar:
    st.header("Settings")
    with st.form("settings"):
        store = st.text_input("Store name", settings["store_name"])
        status = st.text_input("Account status", settings["account_status"])
        fx = st.number_input("Exchange rate (USD per £1)", 0.5, 3.0, FX, 0.01)
        vat_reg = st.checkbox("VAT registered (prices include VAT)", settings["vat_registered"])
        vat = st.number_input("VAT rate %", 0.0, 30.0, float(settings["vat_rate"]) * 100, 1.0)
        signature = st.text_input("Message signature", settings.get("signature", store))
        if st.form_submit_button("Save settings"):
            db.save_settings({"store_name": store, "account_status": status, "usd_per_gbp": fx,
                              "vat_registered": vat_reg, "vat_rate": vat / 100,
                              "signature": signature})
            st.rerun()

    st.header("Backup")
    st.download_button("Download backup (JSON)", json.dumps(db.snapshot(), indent=2, default=str),
                       file_name="seller-control-center.json", mime="application/json")
    up = st.file_uploader("Restore backup", type="json")
    if up is not None and st.button("Restore from file", type="primary"):
        db.load_snapshot(json.load(up))
        bump()
        st.rerun()
    with st.expander("Reset"):
        st.caption("Replaces all data with the starting example.")
        if st.button("Reset to example data"):
            db.init(force_seed=True)
            bump()
            st.rerun()

# ---------------------------------------------------------------- header
st.markdown(
    f'<div class="eyebrow">Amazon seller &nbsp; Marketplace <b>{settings["marketplace"]}</b> &nbsp; '
    f'Sourcing <b>Alibaba</b><br>Store <b>{settings["store_name"]}</b> · {settings["account_status"]}</div>',
    unsafe_allow_html=True,
)
st.title("Seller Control Center")
st.caption(
    "Your products, their margins, the Alibaba suppliers to contact, ready-to-send messages, "
    "orders, listings and ads. Nothing is sent to a supplier or changed on Amazon without you: "
    "payment always stays on your side."
)

tabs = st.tabs(["Overview", "Margins & prices", "Amazon comparison", "Suppliers (Alibaba)",
                "Orders", "Listings & ads", "Launch checklist", "Connections"])

suppliers = db.read("suppliers")
orders = db.read("orders")
checklist = db.read("checklist").sort_values("sort")


def order_total_gbp(row) -> float:
    return ((row["qty"] or 0) * (row["unit_price_usd"] or 0) + (row["shipping_usd"] or 0)) / FX


# ---------------------------------------------------------------- overview
with tabs[0]:
    st.subheader("Where things stand")
    st.caption("Figures are starting assumptions you can change in *Margins & prices*.")
    cols = st.columns(2)
    for i, p in enumerate(products):
        e = econ[p["id"]]
        with cols[i % 2].container(border=True):
            st.markdown(f"**{p['name']}**  \n<span class='sub'>{p['pack']} · selling at "
                        f"{gbp(p['sale_price'])}</span>", unsafe_allow_html=True)
            st.markdown(f"<div class='big'>{gbp(e.profit)}</div>{badge(e.band, e.margin)}"
                        f"<span class='sub'>per unit sold</span>", unsafe_allow_html=True)
            st.markdown(f"<span class='sub'>First order of {p['first_order_qty']} units: about "
                        f"{gbp(e.first_order_cash)} to pay upfront.</span>", unsafe_allow_html=True)

    c1, c2 = st.columns(2)
    with c1.container(border=True):
        st.markdown("**Suppliers**")
        counts = suppliers["status"].value_counts()
        st.dataframe(pd.DataFrame({"Status": db.SUPPLIER_STATUSES,
                                   "Count": [int(counts.get(s, 0)) for s in db.SUPPLIER_STATUSES]}),
                     hide_index=True, width="stretch")
    with c2.container(border=True):
        st.markdown("**Getting started**")
        done = int(checklist["done"].fillna(0).sum())
        total = len(checklist)
        st.markdown(f"<div class='big'>{done / total * 100 if total else 0:.0f} %</div>",
                    unsafe_allow_html=True)
        st.progress(done / total if total else 0.0)
        st.caption(f"{done} of {total} steps complete.")

    c3, c4 = st.columns(2)
    active = orders[orders["status"] != "Cancelled"] if not orders.empty else orders
    total_orders = sum(order_total_gbp(r) for _, r in active.iterrows())
    paid = float(active["paid_gbp"].fillna(0).sum()) if not active.empty else 0.0
    with c3.container(border=True):
        st.markdown("**Orders**")
        st.markdown(f"<div class='big'>{gbp(total_orders - paid)}</div>", unsafe_allow_html=True)
        st.caption(f"left for you to pay. {len(active)} order line(s) tracked, {gbp(paid)} already paid.")
    with c4.container(border=True):
        st.markdown("**Next step**")
        todo = checklist[checklist["done"].fillna(0) == 0]
        st.write(todo.iloc[0]["step"] if not todo.empty else "All steps done 🎉")
        if not todo.empty:
            st.caption(f"Phase: {todo.iloc[0]['phase']}")

# ---------------------------------------------------------------- margins
PCT_COLS = ["duty_pct", "referral_pct", "ads_pct"]
with tabs[1]:
    st.subheader("Margins & prices")
    st.caption("Edit any number, then **Save**. Percentages are in %. Supplier cost is in USD "
               f"(converted at ${FX:.2f} = £1). Fees are per unit in £.")
    pdf = db.read("products")
    pdf[PCT_COLS] = pdf[PCT_COLS] * 100
    with st.form(f"products_{st.session_state.ver}"):
        edited = st.data_editor(
            pdf, num_rows="dynamic", hide_index=True, width="stretch",
            column_order=["name", "pack", "sale_price", "unit_cost_usd", "freight_per_unit",
                          "duty_pct", "referral_pct", "fba_fee", "ads_pct", "other_per_unit",
                          "first_order_qty", "first_order_fixed", "asin", "sku", "notes"],
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
            },
        )
        if st.form_submit_button("Save", type="primary"):
            edited[PCT_COLS] = edited[PCT_COLS] / 100
            db.write("products", edited)
            bump()
            st.rerun()

    rows = []
    for p in products:
        e = econ[p["id"]]
        rows.append({"Product": p["name"], "Price": e.price, "VAT": e.vat, "Referral": e.referral_fee,
                     "FBA": e.fba_fee, "Landed cost": e.landed_cost, "Ads": e.ads, "Other": e.other,
                     "Profit/unit": e.profit, "Margin %": e.margin * 100, "ROI %": e.roi * 100,
                     "Break-even ACoS %": e.breakeven_acos * 100, "1st order £": e.first_order_cash,
                     "Verdict": e.band})
    money = {c: st.column_config.NumberColumn(c, format="£%.2f") for c in
             ["Price", "VAT", "Referral", "FBA", "Landed cost", "Ads", "Other", "Profit/unit",
              "1st order £"]}
    pct = {c: st.column_config.NumberColumn(c, format="%.1f%%") for c in
           ["Margin %", "ROI %", "Break-even ACoS %"]}
    st.markdown("**Results per unit sold**")
    st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch",
                 column_config={**money, **pct})

    if products:
        st.markdown("**What-if: try another price**")
        a, b = st.columns([1, 2])
        pid = a.selectbox("Product", list(prod_names), format_func=prod_names.get, key="whatif")
        p = prod_by_id[pid]
        new_price = a.slider("Sale price £", 1.0, max(50.0, p["sale_price"] * 2),
                             float(p["sale_price"]), 0.5)
        target = a.slider("Target margin %", 5, 40, 20)
        e = calc.unit_economics({**p, "sale_price": new_price}, settings)
        a.metric("Profit per unit", gbp(e.profit), f"{e.margin * 100:.1f}% margin · {e.band}")
        a.caption(f"Price needed for a {target}% margin: "
                  f"**{gbp(calc.price_for_margin(p, settings, target / 100))}**")
        breakdown = pd.DataFrame({"£": [e.vat, e.referral_fee, e.fba_fee, e.landed_cost, e.ads,
                                        e.other, max(e.profit, 0)]},
                                 index=["VAT", "Referral fee", "FBA fee", "Landed cost", "Ads",
                                        "Other", "Profit"])
        b.markdown(f"Where the {gbp(new_price)} goes")
        b.bar_chart(breakdown, horizontal=True)

# ---------------------------------------------------------------- amazon comparison
with tabs[2]:
    st.subheader("Amazon comparison")
    if not products:
        st.info("Add a product first.")
    else:
        pid = st.selectbox("Product", list(prod_names), format_func=prod_names.get, key="cmp")
        p = prod_by_id[pid]
        q = quote_plus(f"{p['name']} {p['pack']}".replace("Christmas:", ""))
        st.markdown(f"[Search amazon.co.uk ↗](https://www.amazon.co.uk/s?k={q}) · "
                    f"[Search Alibaba ↗](https://www.alibaba.com/trade/search?SearchText={q})")
        comp = db.read("competitors")
        mine = comp[comp["product_id"] == pid].drop(columns=["product_id"])
        with st.form(f"comp_{pid}_{st.session_state.ver}"):
            st.caption("Note the top competing listings: price, rating, reviews, Best Sellers Rank.")
            ed = st.data_editor(
                mine, num_rows="dynamic", hide_index=True, width="stretch",
                column_order=["asin", "title", "price", "rating", "reviews", "bsr",
                              "monthly_sales_est", "notes"],
                column_config={
                    "asin": "ASIN", "title": "Title",
                    "price": st.column_config.NumberColumn("Price £", format="%.2f"),
                    "rating": st.column_config.NumberColumn("Rating", min_value=0, max_value=5,
                                                            format="%.1f"),
                    "reviews": st.column_config.NumberColumn("Reviews", format="%d"),
                    "bsr": st.column_config.NumberColumn("BSR", format="%d"),
                    "monthly_sales_est": st.column_config.NumberColumn("Est. sales/month",
                                                                       format="%d"),
                    "notes": "Notes",
                })
            if st.form_submit_button("Save", type="primary"):
                ed["product_id"] = pid
                db.write("competitors", pd.concat([comp[comp["product_id"] != pid], ed]))
                bump()
                st.rerun()
        if not mine.empty and mine["price"].notna().any():
            avg = mine["price"].mean()
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Your price", gbp(p["sale_price"]),
                      f"{(p['sale_price'] / avg - 1) * 100:+.0f}% vs average", delta_color="inverse")
            m2.metric("Competitor average", gbp(avg))
            m3.metric("Lowest / highest", f"{gbp(mine['price'].min())} / {gbp(mine['price'].max())}")
            m4.metric("Median reviews", f"{mine['reviews'].median():,.0f}"
                      if mine["reviews"].notna().any() else "–")
            chart = mine.dropna(subset=["price"]).assign(
                label=lambda d: d["asin"].fillna("").where(d["asin"].fillna("") != "", d["title"]))
            chart = pd.concat([chart[["label", "price"]],
                               pd.DataFrame([{"label": "★ You", "price": p["sale_price"]}])])
            st.bar_chart(chart.set_index("label"))

# ---------------------------------------------------------------- suppliers
with tabs[3]:
    st.subheader("Suppliers (Alibaba)")
    st.caption("Track each supplier through the pipeline. Messages are prepared here; you send "
               "them yourself in Alibaba's message centre.")
    pf = st.selectbox("Show product", ["All", *prod_names.values()], key="sup_filter")
    sdf = suppliers.copy()
    sdf["product"] = sdf["product_id"].map(prod_names)
    sdf["trade_assurance"] = sdf["trade_assurance"].fillna(0).astype(bool)
    view = sdf if pf == "All" else sdf[sdf["product"] == pf]
    with st.form(f"sup_{pf}_{st.session_state.ver}"):
        ed = st.data_editor(
            view, num_rows="dynamic", hide_index=True, width="stretch",
            column_order=["product", "name", "status", "unit_price_usd", "moq", "lead_time_days",
                          "trade_assurance", "years_on_alibaba", "rating", "contact", "url", "notes"],
            column_config={
                "product": st.column_config.SelectboxColumn("Product", options=list(prod_names.values()),
                                                            required=True),
                "name": st.column_config.TextColumn("Supplier", required=True),
                "status": st.column_config.SelectboxColumn("Status", options=db.SUPPLIER_STATUSES,
                                                           default="To contact", required=True),
                "unit_price_usd": st.column_config.NumberColumn("$/unit", format="%.2f"),
                "moq": st.column_config.NumberColumn("MOQ", format="%d"),
                "lead_time_days": st.column_config.NumberColumn("Lead time (days)", format="%d"),
                "trade_assurance": st.column_config.CheckboxColumn("Trade Assurance"),
                "years_on_alibaba": st.column_config.NumberColumn("Years", format="%d"),
                "rating": st.column_config.NumberColumn("Rating", format="%.1f"),
                "contact": "Contact", "url": st.column_config.LinkColumn("Alibaba link"),
                "notes": "Notes",
            })
        if st.form_submit_button("Save", type="primary"):
            ed["product_id"] = ed["product"].map(name_to_pid)
            ed["trade_assurance"] = ed["trade_assurance"].fillna(False).astype(int)
            rest = sdf if pf == "All" else sdf[sdf["product"] != pf]
            out = ed if pf == "All" else pd.concat([rest, ed])
            db.write("suppliers", out.drop(columns=["product"]))
            bump()
            st.rerun()

    st.markdown("**Prepare a message**")
    if suppliers.empty:
        st.info("Add a supplier first.")
    else:
        a, b = st.columns([1, 2])
        sid = a.selectbox("Supplier", suppliers["id"].tolist(),
                          format_func=lambda i: suppliers.set_index("id").loc[i, "name"])
        sup = suppliers.set_index("id").loc[sid].to_dict()
        kind = a.selectbox("Message", list(messages.TEMPLATES))
        prod = prod_by_id.get(sup["product_id"], {})
        text = messages.render(kind, product=prod, supplier=sup, settings=settings,
                               signature=settings.get("signature", ""))
        b.code(text, language=None, wrap_lines=True)
        a.caption("Use the copy icon on the message, paste it into Alibaba, then mark it sent.")
        if sup["status"] in ("To contact", "Message ready") and a.button("Mark as sent"):
            db.update("suppliers", int(sid), {"status": "Sent"})
            bump()
            st.rerun()
        if sup.get("url"):
            a.link_button("Open supplier on Alibaba ↗", sup["url"])

    if not suppliers.empty and suppliers["unit_price_usd"].notna().any():
        st.markdown("**Quote comparison** (landed cost and margin if you buy from this supplier)")
        cmp_rows = []
        for _, s in suppliers.iterrows():
            p = prod_by_id.get(s["product_id"])
            if p is None or pd.isna(s["unit_price_usd"]) or s["status"] == "Rejected":
                continue
            e = calc.unit_economics({**p, "unit_cost_usd": s["unit_price_usd"]}, settings)
            cmp_rows.append({"Product": p["name"], "Supplier": s["name"], "Status": s["status"],
                             "$/unit": s["unit_price_usd"], "MOQ": s["moq"],
                             "Landed £": e.landed_cost, "Profit £": e.profit,
                             "Margin %": e.margin * 100, "Verdict": e.band})
        st.dataframe(pd.DataFrame(cmp_rows).sort_values(["Product", "Profit £"],
                                                         ascending=[True, False]),
                     hide_index=True, width="stretch",
                     column_config={"$/unit": st.column_config.NumberColumn(format="$%.2f"),
                                    "Landed £": st.column_config.NumberColumn(format="£%.2f"),
                                    "Profit £": st.column_config.NumberColumn(format="£%.2f"),
                                    "Margin %": st.column_config.NumberColumn(format="%.1f%%")})

# ---------------------------------------------------------------- orders
with tabs[4]:
    st.subheader("Purchase orders")
    st.caption("Orders you place with suppliers. Pay through Alibaba Trade Assurance; record what "
               "you paid here.")
    sup_names = dict(zip(suppliers["id"], suppliers["name"]))
    sup_by_name = {v: k for k, v in sup_names.items()}
    odf = orders.copy()
    odf["product"] = odf["product_id"].map(prod_names)
    odf["supplier"] = odf["supplier_id"].map(sup_names)
    odf["order_date"] = pd.to_datetime(odf["order_date"], errors="coerce").dt.date
    odf["eta"] = pd.to_datetime(odf["eta"], errors="coerce").dt.date
    with st.form(f"orders_{st.session_state.ver}"):
        ed = st.data_editor(
            odf, num_rows="dynamic", hide_index=True, width="stretch",
            column_order=["order_date", "product", "supplier", "qty", "unit_price_usd",
                          "shipping_usd", "status", "paid_gbp", "tracking", "eta", "notes"],
            column_config={
                "order_date": st.column_config.DateColumn("Date"),
                "product": st.column_config.SelectboxColumn("Product", options=list(prod_names.values()),
                                                            required=True),
                "supplier": st.column_config.SelectboxColumn("Supplier", options=list(sup_names.values())),
                "qty": st.column_config.NumberColumn("Qty", format="%d", min_value=0),
                "unit_price_usd": st.column_config.NumberColumn("$/unit", format="%.2f"),
                "shipping_usd": st.column_config.NumberColumn("Shipping $", format="%.2f"),
                "status": st.column_config.SelectboxColumn("Status", options=db.ORDER_STATUSES,
                                                           default="Draft", required=True),
                "paid_gbp": st.column_config.NumberColumn("Paid £", format="%.2f"),
                "tracking": "Tracking", "eta": st.column_config.DateColumn("ETA"), "notes": "Notes",
            })
        if st.form_submit_button("Save", type="primary"):
            ed["product_id"] = ed["product"].map(name_to_pid)
            ed["supplier_id"] = ed["supplier"].map(sup_by_name)
            for c in ("order_date", "eta"):
                ed[c] = ed[c].astype(str).replace({"None": None, "NaT": None})
            db.write("orders", ed.drop(columns=["product", "supplier"]))
            bump()
            st.rerun()
    if not orders.empty:
        t = orders.assign(total=orders.apply(order_total_gbp, axis=1))
        t = t[t["status"] != "Cancelled"]
        m1, m2, m3 = st.columns(3)
        m1.metric("Total ordered", gbp(t["total"].sum()))
        m2.metric("Paid", gbp(t["paid_gbp"].fillna(0).sum()))
        m3.metric("Still to pay", gbp(t["total"].sum() - t["paid_gbp"].fillna(0).sum()))

# ---------------------------------------------------------------- listings & ads
with tabs[5]:
    st.subheader("Listings & ads")
    if not products:
        st.info("Add a product first.")
    else:
        pid = st.selectbox("Product", list(prod_names), format_func=prod_names.get, key="lst")
        p, e = prod_by_id[pid], econ[pid]
        listings = db.read("listings")
        cur = listings[listings["product_id"] == pid]
        lst = cur.iloc[0].to_dict() if not cur.empty else {}
        left, right = st.columns(2)
        with left, st.form(f"listing_{pid}_{st.session_state.ver}"):
            st.markdown("**Listing draft**")
            title = st.text_input("Title (max 200 characters)", lst.get("title") or "", max_chars=200)
            bullets = st.text_area("Bullet points (one per line, 5 recommended)",
                                   lst.get("bullets") or "", height=160)
            desc = st.text_area("Description", lst.get("description") or "", height=120)
            terms = st.text_input("Backend search terms (max 249 bytes)", lst.get("search_terms") or "")
            lstatus = st.selectbox("Status", ["Draft", "Ready", "Published"],
                                   index=["Draft", "Ready", "Published"].index(lst.get("status") or "Draft"))
            nb = len([b for b in bullets.splitlines() if b.strip()])
            nbytes = len(terms.encode())
            st.caption(f"{len(title)}/200 title chars · {nb}/5 bullets · {nbytes}/249 search-term bytes")
            if nbytes > 249:
                st.warning("Search terms exceed 249 bytes: Amazon will ignore them.")
            if st.form_submit_button("Save listing", type="primary"):
                vals = {"product_id": pid, "title": title, "bullets": bullets, "description": desc,
                        "search_terms": terms, "status": lstatus}
                if lst:
                    db.update("listings", int(lst["id"]), vals)
                else:
                    db.insert("listings", vals)
                bump()
                st.rerun()
            st.caption("Copy into Seller Central → Catalogue → Add products. "
                       "Nothing is published from here.")

        with right:
            st.markdown("**Sponsored Products plan**")
            ads = db.read("ads")
            curad = ads[ads["product_id"] == pid]
            ad = curad.iloc[0].to_dict() if not curad.empty else {}
            with st.form(f"ads_{pid}_{st.session_state.ver}"):
                camp = st.text_input("Campaign name", ad.get("campaign") or f"SP - {p['name']}")
                budget = st.number_input("Daily budget £", 1.0, 1000.0, float(ad.get("daily_budget") or 5), 1.0)
                cpc = st.number_input("Expected cost per click £", 0.05, 10.0, float(ad.get("cpc") or 0.45), 0.05)
                cr = st.number_input("Conversion rate %", 1.0, 50.0, float(ad.get("conversion_rate") or 0.1) * 100, 1.0)
                kw = st.text_area("Keywords (one per line)", ad.get("keywords") or "", height=100)
                if st.form_submit_button("Save plan", type="primary"):
                    vals = {"product_id": pid, "campaign": camp, "daily_budget": budget, "cpc": cpc,
                            "conversion_rate": cr / 100, "keywords": kw, "status": ad.get("status") or "Planned"}
                    if ad:
                        db.update("ads", int(ad["id"]), vals)
                    else:
                        db.insert("ads", vals)
                    bump()
                    st.rerun()
            f = calc.ads_forecast(float(ad.get("daily_budget") or 5), float(ad.get("cpc") or 0.45),
                                  float(ad.get("conversion_rate") or 0.1), p["sale_price"])
            m1, m2, m3 = st.columns(3)
            m1.metric("Clicks/day", f"{f['clicks']:.0f}")
            m2.metric("Ad orders/day", f"{f['orders']:.1f}")
            m3.metric("Expected ACoS", f"{f['acos'] * 100:.0f}%")
            be = e.breakeven_acos
            if f["acos"] > be:
                st.warning(f"Expected ACoS is above your break-even ACoS of {be * 100:.0f}%: "
                           "each ad sale loses money. Lower the CPC, raise the price or improve conversion.")
            else:
                st.success(f"Expected ACoS is below your break-even ACoS of {be * 100:.0f}%.")

# ---------------------------------------------------------------- checklist
with tabs[6]:
    st.subheader("Launch checklist")
    cdf = checklist.copy()
    cdf["done"] = cdf["done"].fillna(0).astype(bool)
    with st.form(f"check_{st.session_state.ver}"):
        ed = st.data_editor(
            cdf, num_rows="dynamic", hide_index=True, width="stretch",
            column_order=["done", "phase", "step"],
            column_config={"done": st.column_config.CheckboxColumn("Done", width="small"),
                           "phase": st.column_config.TextColumn("Phase", width="medium"),
                           "step": st.column_config.TextColumn("Step", width="large", required=True)})
        if st.form_submit_button("Save", type="primary"):
            ed["done"] = ed["done"].fillna(False).astype(int)
            ed["sort"] = range(1, len(ed) + 1)
            db.write("checklist", ed)
            bump()
            st.rerun()

# ---------------------------------------------------------------- connections
with tabs[7]:
    connections.render(products, prod_names)

st.divider()
st.caption("Data is stored in a local SQLite file on the machine running this app. "
           "Use **Download backup** in the sidebar to keep a copy.")
