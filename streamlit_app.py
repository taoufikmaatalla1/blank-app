"""TASOH Seller: one dashboard to buy on Alibaba and sell on Amazon UK."""

from __future__ import annotations

import json

import streamlit as st

from pilot import connections, db, ui
from pilot.integrations import mailer
from pilot.views import (checklist, competition, customer_orders, dashboard, fba, listings,
                         products, purchases, quotes, research, treasury)

st.set_page_config(page_title="TASOH Seller", page_icon="📦", layout="wide")
st.markdown(ui.CSS, unsafe_allow_html=True)
db.init()
settings = db.get_settings()

# Alibaba sends the user back here after connecting the account (?code=...), on any page.
connections.handle_alibaba_callback()

# ---------------------------------------------------------------- menu
PAGE_DEFS = [
    ("Dashboard", "🏠", dashboard.render, "dashboard"),
    ("Product search", "🔎", research.render, "search"),
    ("Supplier quotes", "✉️", quotes.render, "quotes"),
    ("Purchases & payments", "🧾", purchases.render, "purchases"),
    ("Products & margins", "📊", products.render, "products"),
    ("Amazon competition", "🆚", competition.render, "competition"),
    ("Listings & ads", "📢", listings.render, "listings"),
    ("Stock & FBA shipments", "🚚", fba.render, "fba"),
    ("Customer orders", "🛒", customer_orders.render, "customer-orders"),
    ("Cash", "💷", treasury.render, "cash"),
    ("Launch checklist", "✅", checklist.render, "checklist"),
    ("Connections", "🔌", connections.render, "connections"),
]
pages = {title: st.Page(fn, title=title, icon=icon, url_path=path, default=(i == 0))
         for i, (title, icon, fn, path) in enumerate(PAGE_DEFS)}
ui.PAGES.update(pages)
nav = st.navigation({
    "Overview": [pages["Dashboard"]],
    "Buy (Alibaba)": [pages[t] for t in ("Product search", "Supplier quotes", "Purchases & payments")],
    "Sell (Amazon)": [pages[t] for t in ("Products & margins", "Amazon competition", "Listings & ads",
                                         "Stock & FBA shipments", "Customer orders")],
    "Money & setup": [pages[t] for t in ("Cash", "Launch checklist", "Connections")],
})

# ---------------------------------------------------------------- sidebar
with st.sidebar:
    with st.expander("⚙️ Settings"):
        with st.form("settings"):
            store = st.text_input("Store name", settings["store_name"])
            status = st.text_input("Account status", settings["account_status"])
            fx = st.number_input("Exchange rate (USD per £1)", 0.5, 3.0, float(settings["usd_per_gbp"]), 0.01)
            vat_reg = st.checkbox("VAT registered (prices include VAT)", settings["vat_registered"])
            vat = st.number_input("VAT rate %", 0.0, 30.0, float(settings["vat_rate"]) * 100, 1.0)
            signature = st.text_input("Message signature", settings.get("signature", store))
            if st.form_submit_button("Save settings"):
                db.save_settings({"store_name": store, "account_status": status, "usd_per_gbp": fx,
                                  "vat_registered": vat_reg, "vat_rate": vat / 100,
                                  "signature": signature})
                st.rerun()
    with st.expander("💾 Backup"):
        st.caption("Streamlit Cloud erases the data when the app restarts. Download a backup after "
                   "making changes.")
        st.download_button("Download backup (JSON)", json.dumps(db.snapshot(), indent=2, default=str),
                           file_name="tasoh-seller-backup.json", mime="application/json")
        up = st.file_uploader("Restore backup", type="json")
        if up is not None and st.button("Restore from file", type="primary"):
            db.load_snapshot(json.load(up))
            db.init()  # adds any columns missing from an older backup
            ui.bump()
            st.rerun()
        if st.button("Reset to example data"):
            db.init(force_seed=True)
            ui.bump()
            st.rerun()
    st.caption(f"Gmail: {'✅ ' + mailer.sender() if mailer.configured() else '❌ not set up'}")

st.markdown(
    f'<div class="eyebrow">Amazon seller &nbsp; Marketplace <b>{settings["marketplace"]}</b> &nbsp; '
    f'Sourcing <b>Alibaba</b> &nbsp;·&nbsp; Store <b>{settings["store_name"]}</b> · '
    f'{settings["account_status"]}</div>', unsafe_allow_html=True)
ui.show_flash()
nav.run()
