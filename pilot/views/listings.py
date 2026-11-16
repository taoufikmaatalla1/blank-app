"""Listings & ads: write the listing, plan advertising, change the price on Amazon."""

from __future__ import annotations

import streamlit as st

from .. import calc, db, ui
from ..connections import show_error
from ..integrations import AmazonClient, AmazonError, factory
from ..i18n import t

LISTING_STATUSES = ["Draft", "Ready", "Published"]


def render() -> None:
    ctx = ui.load()
    st.title(t("📢 Listings & ads"))
    if not ctx.products:
        st.info(t("Add a product first."))
        return
    st.info(t("Coming in part 2: publish the listing straight to Amazon from this page, with your EAN "
            "barcode. Until then, copy the text into Seller Central → Catalogue → Add products, then "
            "set the status to \"Published\"."))
    names = ctx.prod_names
    pid = st.selectbox(t("Product"), list(names), format_func=names.get, key="lst")
    p, e = ctx.prod_by_id[pid], ctx.econ[pid]
    listings = ctx.listings
    cur = listings[listings["product_id"] == pid]
    lst = cur.iloc[0].to_dict() if not cur.empty else {}
    left, right = st.columns(2)
    with left, st.form(f"listing_{pid}_{ui.ver()}"):
        st.markdown(t("**Listing**"))
        title = st.text_input(t("Title (max 200 characters)"), lst.get("title") or "", max_chars=200)
        bullets = st.text_area(t("Bullet points (one per line, 5 recommended)"), lst.get("bullets") or "", height=160)
        desc = st.text_area(t("Description"), lst.get("description") or "", height=120)
        terms = st.text_input(t("Backend search terms (max 249 bytes)"), lst.get("search_terms") or "")
        status = lst.get("status") if lst.get("status") in LISTING_STATUSES else "Draft"
        lstatus = st.selectbox(t("Status"), LISTING_STATUSES, index=LISTING_STATUSES.index(status), format_func=t)
        nb = len([b for b in bullets.splitlines() if b.strip()])
        nbytes = len(terms.encode())
        st.caption(t("{chars}/200 title chars · {nb}/5 bullets · {nbytes}/249 search-term bytes",
                     chars=len(title), nb=nb, nbytes=nbytes))
        if nbytes > 249:
            st.warning(t("Search terms exceed 249 bytes: Amazon will ignore them."))
        if st.form_submit_button(t("Save listing"), type="primary"):
            vals = {"product_id": pid, "title": title, "bullets": bullets, "description": desc,
                    "search_terms": terms, "status": lstatus}
            if lst:
                db.update("listings", int(lst["id"]), vals)
            else:
                db.insert("listings", vals)
            ui.bump()
            st.rerun()

    with right:
        st.markdown(t("**Sponsored Products plan**"))
        ads = db.read("ads")
        curad = ads[ads["product_id"] == pid]
        ad = curad.iloc[0].to_dict() if not curad.empty else {}
        with st.form(f"ads_{pid}_{ui.ver()}"):
            camp = st.text_input(t("Campaign name"), ad.get("campaign") or f"SP - {p['name']}")
            budget = st.number_input(t("Daily budget £"), 1.0, 1000.0, float(ad.get("daily_budget") or 5), 1.0)
            cpc = st.number_input(t("Expected cost per click £"), 0.05, 10.0, float(ad.get("cpc") or 0.45), 0.05)
            cr = st.number_input(t("Conversion rate %"), 1.0, 50.0, float(ad.get("conversion_rate") or 0.1) * 100, 1.0)
            kw = st.text_area(t("Keywords (one per line)"), ad.get("keywords") or "", height=100)
            if st.form_submit_button(t("Save plan"), type="primary"):
                vals = {"product_id": pid, "campaign": camp, "daily_budget": budget, "cpc": cpc,
                        "conversion_rate": cr / 100, "keywords": kw, "status": ad.get("status") or "Planned"}
                if ad:
                    db.update("ads", int(ad["id"]), vals)
                else:
                    db.insert("ads", vals)
                ui.bump()
                st.rerun()
        f = calc.ads_forecast(float(ad.get("daily_budget") or 5), float(ad.get("cpc") or 0.45),
                              float(ad.get("conversion_rate") or 0.1), p["sale_price"])
        m1, m2, m3 = st.columns(3)
        m1.metric(t("Clicks/day"), f"{f['clicks']:.0f}")
        m2.metric(t("Ad orders/day"), f"{f['orders']:.1f}")
        m3.metric(t("Expected ACoS"), f"{f['acos'] * 100:.0f}%")
        if f["acos"] > e.breakeven_acos:
            st.warning(t("Expected ACoS is above your break-even ACoS of {be:.0f}%: each ad sale loses "
                         "money. Lower the CPC or raise the price.", be=e.breakeven_acos * 100))
        else:
            st.success(t("Expected ACoS is below your break-even ACoS of {be:.0f}%.", be=e.breakeven_acos * 100))
        st.caption(t("Coming in part 3: create the campaign on Amazon from here (needs Amazon Ads API access)."))

    st.subheader(t("Change the price on Amazon"))
    if not AmazonClient.configured():
        st.caption(t("Connect Amazon (Connections page) to change prices from here."))
    elif not p.get("sku"):
        st.caption(t("Add this product's SKU in Products & margins."))
    else:
        with st.form(f"amz_price_{pid}"):
            price = st.number_input(t("New price £ (incl. VAT)"), 0.5, 1000.0, float(p["sale_price"]), 0.1)
            ptype = st.text_input(t("Amazon product type"), "PRODUCT", help=t("As shown on the listing, e.g. PHONE_ACCESSORY"))
            sure = st.checkbox(t("I approve changing {sku} on Amazon to {price}", sku=p["sku"], price=ui.gbp(price)))
            if st.form_submit_button(t("Update price on Amazon"), type="primary"):
                if not sure:
                    st.warning(t("Tick the approval box first."))
                else:
                    try:
                        res = factory.amazon().update_price(p["sku"], price, ptype)
                        db.update("products", int(pid), {"sale_price": price})
                        st.success(t("Amazon answered: {status}", status=res.get("status", "OK")))
                        if res.get("issues"):
                            st.json(res["issues"])
                    except AmazonError as err:
                        show_error(err)
