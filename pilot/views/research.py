"""Step 1: search products on Alibaba and Amazon, estimate the margin, add the best to the pipeline."""

from __future__ import annotations

import statistics
from urllib.parse import quote_plus

import pandas as pd
import streamlit as st

from .. import calc, db, ui
from ..connections import alibaba_ready, show_error
from ..integrations import AlibabaError, AmazonClient, AmazonError, factory
from ..integrations.alibaba import first_price
from ..i18n import cols, t, table


def _amazon_price(offers: dict) -> float | None:
    summ = offers.get("Summary") or {}
    for key in ("BuyBoxPrices", "LowestPrices"):
        for p in summ.get(key) or []:
            amt = (p.get("LandedPrice") or p.get("ListingPrice") or {}).get("Amount")
            if amt:
                return float(amt)
    return None


def render() -> None:
    ctx = ui.load()
    st.title(t("🔎 Product search"))
    st.caption(t("Type a product: the app looks up supplier prices on Alibaba and the competition on "
               "Amazon, then estimates your margin. Add the best ones to your pipeline."))

    with st.form("search"):
        c1, c2 = st.columns([3, 1])
        kw = c1.text_input(t("Product to search"), st.session_state.get("r_kw", ""),
                           placeholder=t("e.g. magnetic screwdriver set"))
        target = c2.number_input(t("Target selling price £"), 1.0, 500.0,
                                 float(st.session_state.get("r_target", 12.99)), 0.5,
                                 help=t("Replaced by the average Amazon price when Amazon prices are loaded."))
        go = st.form_submit_button(t("Search"), type="primary")
    if go and kw:
        st.session_state.r_kw, st.session_state.r_target = kw, target
        st.session_state.r_ali, st.session_state.r_amz = None, None
        st.session_state.r_amz_prices = {}
        if alibaba_ready():
            try:
                st.session_state.r_ali = factory.alibaba().search(kw, size=30)["products"]
            except AlibabaError as e:
                show_error(e)
        if AmazonClient.configured():
            try:
                st.session_state.r_amz = factory.amazon().search_catalog(kw, page_size=10)
            except AmazonError as e:
                show_error(e)

    kw = st.session_state.get("r_kw", "")
    if kw:
        q = quote_plus(kw)
        b1, b2 = st.columns(2)
        b1.link_button(t("Open on alibaba.com ↗"), f"https://www.alibaba.com/trade/search?SearchText={q}")
        b2.link_button(t("Open on amazon.co.uk ↗"), f"https://www.amazon.co.uk/s?k={q}")

    hyp = ui.research_defaults(ctx.settings)
    with st.expander(t("Assumptions (Amazon fees, freight…)")):
        h1, h2, h3 = st.columns(3)
        hyp["fba_fee"] = h1.number_input(t("FBA fee £/unit"), 0.0, 50.0, hyp["fba_fee"], 0.1)
        hyp["referral_pct"] = h2.number_input(t("Amazon referral %"), 0.0, 50.0, hyp["referral_pct"] * 100, 1.0) / 100
        hyp["freight_per_unit"] = h3.number_input(t("Freight £/unit"), 0.0, 50.0, hyp["freight_per_unit"], 0.05)
        hyp["ads_pct"] = h1.number_input(t("Ads % of price"), 0.0, 50.0, hyp["ads_pct"] * 100, 1.0) / 100
        hyp["duty_pct"] = h2.number_input(t("Import duty %"), 0.0, 50.0, hyp["duty_pct"] * 100, 0.5) / 100
        st.caption(t("These are estimates. Real fees come from Amazon once the ASIN is known "
                   "(Connections → Update fees from Amazon)."))

    target = float(st.session_state.get("r_target", 12.99))

    # ------------------------------------------------------------ Amazon
    st.subheader(t("Competition on Amazon"))
    amz = st.session_state.get("r_amz")
    if not AmazonClient.configured():
        st.info(t("Amazon is not connected: use the \"Open on amazon.co.uk\" button above."))
    elif amz is None:
        st.caption(t("Run a search."))
    elif not amz:
        st.caption(t("No Amazon results."))
    else:
        prices = st.session_state.get("r_amz_prices", {})
        rows = []
        for it in amz:
            s = (it.get("summaries") or [{}])[0]
            ranks = (it.get("salesRanks") or [{}])[0]
            rank = (ranks.get("displayGroupRanks") or ranks.get("classificationRanks") or [{}])[0].get("rank")
            rows.append({"ASIN": it.get("asin"), "Title": s.get("itemName"), "Brand": s.get("brand"),
                         "Sales rank": rank, "Price £": prices.get(it.get("asin"))})
        if st.button(t("Load prices for the top 5")):
            client, new = factory.amazon(), {}
            for r in rows[:5]:
                try:
                    new[r["ASIN"]] = _amazon_price(client.item_offers(r["ASIN"]))
                except AmazonError:
                    new[r["ASIN"]] = None
            st.session_state.r_amz_prices = new
            found = [p for p in new.values() if p]
            if found:
                st.session_state.r_target = round(statistics.mean(found), 2)
            st.rerun()
        table(pd.DataFrame(rows), {"Price £": st.column_config.NumberColumn(format="£%.2f")})
        found = [p for p in prices.values() if p]
        if found:
            st.caption(t("Amazon prices: average {avg}, from {low} to {high}. Target price used: {target}.",
                         avg=ui.gbp(statistics.mean(found)), low=ui.gbp(min(found)),
                         high=ui.gbp(max(found)), target=ui.gbp(target)))

    # ------------------------------------------------------------ Alibaba
    st.subheader(t("Suppliers on Alibaba"))
    cands = list(st.session_state.get("r_ali") or [])
    if not alibaba_ready():
        st.info(t("Alibaba is not connected yet (permissions pending). Meanwhile, add products you find "
                "on alibaba.com with the form below."))
    with st.expander(t("➕ Add a product found on alibaba.com by hand"), expanded=not alibaba_ready()):
        with st.form("manual", clear_on_submit=True):
            m1, m2 = st.columns([3, 1])
            title = m1.text_input(t("Product / supplier name"))
            price = m2.number_input(t("Price $/unit"), 0.0, 10000.0, 0.0, 0.01)
            m3, m4 = st.columns([3, 1])
            url = m3.text_input(t("Alibaba link (product page)"))
            moq = m4.number_input(t("Minimum order (MOQ)"), 0, 1_000_000, 0, 10)
            if st.form_submit_button(t("Add to the list")) and title and price > 0:
                st.session_state.setdefault("r_manual", []).append(
                    {"title": title, "price": price, "permalink": url, "moq": moq or None, "product_id": ""})
                st.rerun()
    cands += st.session_state.get("r_manual", [])
    if not cands:
        st.caption(t("No products yet."))
        return

    rows = []
    for c in cands:
        p_usd = first_price(c.get("price"))
        e = calc.unit_economics({**hyp, "sale_price": target, "unit_cost_usd": p_usd or 0,
                                 "first_order_qty": c.get("moq") or 0}, ctx.settings)
        img = c.get("image")
        rows.append({"Pick": False, "Product": c.get("title"), "Price $": p_usd,
                     "Landed cost £": e.landed_cost, "Profit £/unit": e.profit,
                     "Margin %": e.margin * 100, "Verdict": e.band,
                     "Image": img.get("main_image") if isinstance(img, dict) else None,
                     "Link": c.get("permalink"), "ID": str(c.get("product_id") or ""), "MOQ": c.get("moq")})
    df = pd.DataFrame(rows).sort_values("Profit £/unit", ascending=False)
    df["Verdict"] = df["Verdict"].map(t)
    st.caption(t("Estimated margin when selling at {price}, most profitable first.", price=ui.gbp(target)))
    picked = st.data_editor(
        df, hide_index=True, width="stretch", key=f"r_pick_{ui.ver()}",
        disabled=[c for c in df.columns if c != "Pick"],
        column_order=["Pick", "Image", "Product", "Price $", "Landed cost £", "Profit £/unit",
                      "Margin %", "Verdict", "Link"],
        column_config=cols(columns=["Product", "Verdict"], config={
            "Pick": st.column_config.CheckboxColumn(width="small"),
            "Image": st.column_config.ImageColumn(width="small"),
            "Price $": st.column_config.NumberColumn(format="$%.2f"),
            "Landed cost £": st.column_config.NumberColumn(format="£%.2f"),
            "Profit £/unit": st.column_config.NumberColumn(format="£%.2f"),
            "Margin %": st.column_config.NumberColumn(format="%.1f%%"),
            "Link": st.column_config.LinkColumn(display_text=t("Open ↗")),
        }))
    chosen = picked[picked["Pick"]]

    st.markdown(t("**Add the ticked products to your pipeline**"))
    names = ctx.prod_names
    with st.form("add_pipeline"):
        mode = st.radio(t("Add them to"), ["A new product", "An existing product"], horizontal=True,
                        format_func=t)
        n1, n2, n3 = st.columns([2, 1, 1])
        new_name = n1.text_input(t("New product name"), kw.capitalize() if kw else "")
        new_pack = n2.text_input(t("Pack"), "Single")
        existing = n3.selectbox(t("Existing product"), list(names), format_func=names.get) if names else None
        submitted = st.form_submit_button(t("Add {n} supplier(s) to the pipeline", n=len(chosen)), type="primary")
    if submitted:
        if chosen.empty:
            st.warning(t("Tick at least one product in the table."))
            return
        if mode == "A new product":
            if not new_name:
                st.warning(t("Give the product a name."))
                return
            best = chosen.iloc[0]
            pid = db.insert("products", {
                **hyp, "name": new_name, "pack": new_pack, "sale_price": target,
                "unit_cost_usd": best["Price $"] or 0,
                "first_order_qty": int(best["MOQ"]) if pd.notna(best["MOQ"]) and best["MOQ"] else 100,
                "asin": "", "sku": "", "notes": f"Search: {kw}"})
        else:
            pid = existing
        for _, r in chosen.iterrows():
            db.insert("suppliers", {
                "product_id": pid, "name": (r["Product"] or "")[:120], "url": r["Link"] or "",
                "status": "To contact", "unit_price_usd": r["Price $"],
                "moq": int(r["MOQ"]) if pd.notna(r["MOQ"]) and r["MOQ"] else None,
                "trade_assurance": 1, "alibaba_product_id": r["ID"],
                "notes": f"Found by searching \"{kw}\""})
        ui.bump()
        ui.flash(t("Added {n} supplier(s). Next step: ask them for a price.", n=len(chosen)))
        st.switch_page(ui.PAGES["Supplier quotes"])
