"""Step 2: ask suppliers for a price, record their quotes, compare them and pick one."""

from __future__ import annotations

from datetime import date, datetime, timezone

import pandas as pd
import streamlit as st

from .. import calc, db, messages, ui
from ..integrations import mailer
from ..i18n import from_display, options, t, table, to_display


def _log(supplier: dict, pid: int, channel: str, to: str, subject: str, body: str, status: str) -> None:
    db.insert("messages", {
        "supplier_id": int(supplier["id"]), "product_id": pid, "channel": channel, "to_address": to,
        "subject": subject, "body": body, "status": status,
        "sent_at": datetime.now(timezone.utc).isoformat(timespec="seconds")})


def quote_economics(product: dict, supplier: dict, settings: dict) -> calc.Economics:
    """Margin if you buy from this supplier, using its price, MOQ and shipping cost."""
    fx = float(settings["usd_per_gbp"])
    moq = supplier.get("moq") or product.get("first_order_qty") or 0
    ship = supplier.get("shipping_usd")
    over = {"unit_cost_usd": supplier.get("unit_price_usd") or 0, "first_order_qty": moq}
    if ship and moq:
        over["freight_per_unit"] = float(ship) / float(moq) / fx
    return calc.unit_economics({**product, **over}, settings)


def render() -> None:
    ctx = ui.load()
    st.title(t("✉️ Supplier quotes"))
    st.caption(t("Ask several suppliers for a price, record their answers, compare the margin you "
               "would make with each, and pick the best."))
    if not ctx.products:
        st.info(t("No products yet. Start with Product search."))
        ui.link("Product search", t("Go to Product search →"), "🔎")
        return

    names = ctx.prod_names
    with_sup = [pid for pid in names if (ctx.suppliers["product_id"] == pid).any()]
    if st.session_state.get("q_pid") not in names:
        st.session_state.q_pid = with_sup[-1] if with_sup else list(names)[0]
    pid = st.selectbox(t("Product"), list(names), format_func=lambda i: f"{names[i]}  ·  {t(ctx.stage(i))}",
                       key="q_pid")
    product = ctx.prod_by_id[pid]
    sup_df = ctx.suppliers[ctx.suppliers["product_id"] == pid]
    sups = ctx.records(sup_df)
    if not sups:
        st.info(t("No suppliers for this product yet. Add some from Product search."))
        ui.link("Product search", t("Go to Product search →"), "🔎")
        return

    # ------------------------------------------------------------ 1. suppliers
    st.subheader(t("1. Suppliers for this product"))
    st.caption(t("Add a supplier's e-mail if they gave it to you: quote requests can then be sent "
               "straight from your Gmail."))
    with st.form(f"q_sup_{pid}_{ui.ver()}"):
        ed = st.data_editor(
            to_display(sup_df, "status"), hide_index=True, width="stretch", num_rows="dynamic",
            column_order=["name", "status", "email", "contact", "unit_price_usd", "moq", "shipping_usd",
                          "lead_time_days", "url", "notes"],
            column_config={
                "name": st.column_config.TextColumn(t("Supplier"), required=True),
                "status": st.column_config.SelectboxColumn(t("Status"), options=options(db.SUPPLIER_STATUSES),
                                                           default=t("To contact"), required=True),
                "email": st.column_config.TextColumn(t("E-mail")),
                "contact": t("Contact"),
                "unit_price_usd": st.column_config.NumberColumn(t("Price $/unit"), format="%.2f"),
                "moq": st.column_config.NumberColumn(t("MOQ"), format="%d"),
                "shipping_usd": st.column_config.NumberColumn(t("Shipping total $"), format="%.2f"),
                "lead_time_days": st.column_config.NumberColumn(t("Lead time (days)"), format="%d"),
                "url": st.column_config.LinkColumn(t("Alibaba link")),
                "notes": t("Notes"),
            })
        if st.form_submit_button(t("Save")):
            ed = from_display(ed, "status")
            ed["product_id"] = pid
            db.write("suppliers", pd.concat([ctx.suppliers[ctx.suppliers["product_id"] != pid], ed]))
            ui.bump()
            st.rerun()

    # ------------------------------------------------------------ 2. request a price
    st.subheader(t("2. Ask for a price"))
    sig = ctx.settings.get("signature") or ctx.settings.get("store_name", "")
    by_id = {s["id"]: s for s in sups}
    to_contact = [s["id"] for s in sups if s["status"] in ("To contact", "Message ready")]
    chosen = st.multiselect(t("Send to"), list(by_id), default=to_contact, format_func=lambda i: by_id[i]["name"],
                            placeholder=t("Choose suppliers"))
    kind = st.selectbox(t("Message"), list(messages.TEMPLATES), format_func=lambda k: t(messages.LABELS[k]))
    model = {"moq": product.get("first_order_qty"), "unit_price_usd": product.get("unit_cost_usd")}
    subject = st.text_input(t("Subject"), messages.subject(kind, product=product, supplier=model,
                                                        settings=ctx.settings), key=f"q_subj_{pid}_{kind}")
    body = st.text_area(t("Message (you can edit it)"),
                        messages.render(kind, product=product, supplier=model, settings=ctx.settings,
                                        signature=sig), height=320, key=f"q_body_{pid}_{kind}")
    targets = [by_id[i] for i in chosen]
    with_mail = [s for s in targets if s.get("email")]
    without = [s for s in targets if not s.get("email")]

    if with_mail:
        st.markdown(t("**📧 By e-mail** ({n}):", n=len(with_mail)) + " " +
                    ", ".join(f"{s['name']} <{s['email']}>" for s in with_mail))
        if not mailer.configured():
            st.warning(t("Gmail is not set up: see Connections → Gmail."))
        else:
            ok = st.checkbox(t("I approve sending this message to {n} supplier(s) from {sender}",
                               n=len(with_mail), sender=mailer.sender()))
            if st.button(t("Send e-mails"), type="primary", disabled=not ok):
                sent = 0
                for s in with_mail:
                    try:
                        mailer.send(s["email"], subject, body, from_name=ctx.settings.get("store_name", ""))
                        _log(s, pid, "e-mail", s["email"], subject, body, "sent")
                        if s["status"] in ("To contact", "Message ready"):
                            db.update("suppliers", int(s["id"]), {"status": "Sent"})
                        sent += 1
                    except mailer.MailError as e:
                        _log(s, pid, "e-mail", s["email"], subject, body, f"failed: {e}")
                        st.error(f"{s['name']}: {e}")
                ui.bump()
                ui.flash(t("{n} e-mail(s) sent.", n=sent))
                st.rerun()
    if without:
        st.markdown(t("**💬 Through Alibaba messages** ({n}): Alibaba does not share "
                    "suppliers' e-mail addresses. Open the supplier's page, click **Contact Supplier** "
                    "and paste the message (copy icon below).", n=len(without)))
        st.code(body, language=None, wrap_lines=True)
        for s in without:
            c1, c2 = st.columns([3, 1])
            if s.get("url"):
                c1.link_button(t("Open {name} on Alibaba ↗", name=s["name"][:60]), s["url"])
            else:
                c1.write(t("{name} (no link saved)", name=s["name"]))
            if c2.button(t("Mark as sent"), key=f"sent_{s['id']}"):
                _log(s, pid, "Alibaba", "", subject, body, "sent")
                db.update("suppliers", int(s["id"]), {"status": "Sent"})
                ui.bump()
                st.rerun()

    # ------------------------------------------------------------ 3. record a quote
    st.subheader(t("3. Record a quote you received"))
    with st.form(f"q_quote_{pid}", clear_on_submit=True):
        sid = st.selectbox(t("Supplier"), list(by_id), format_func=lambda i: by_id[i]["name"])
        c1, c2, c3 = st.columns(3)
        price = c1.number_input(t("Price $/unit"), 0.0, 100000.0, 0.0, 0.01)
        moq = c2.number_input(t("Minimum order (MOQ)"), 0, 1_000_000, 0, 10)
        ship = c3.number_input(t("Shipping to the UK, total $"), 0.0, 1_000_000.0, 0.0, 1.0,
                               help=t("Leave 0 if unknown: the product's freight estimate is used."))
        c4, c5 = st.columns(2)
        lead = c4.number_input(t("Production lead time (days)"), 0, 365, 0)
        sample = c5.number_input(t("Sample price $"), 0.0, 10000.0, 0.0, 1.0)
        notes = st.text_input(t("Notes (options, logo, packaging…)"))
        if st.form_submit_button(t("Save quote"), type="primary"):
            if price <= 0:
                st.warning(t("Enter the unit price."))
            else:
                vals = {"unit_price_usd": price, "status": "Quote received", "quote_date": date.today().isoformat()}
                for key, val in (("moq", moq), ("shipping_usd", ship), ("lead_time_days", lead),
                                 ("sample_cost_usd", sample), ("notes", notes)):
                    if val:
                        vals[key] = val
                db.update("suppliers", int(sid), vals)
                ui.bump()
                ui.flash(t("Quote saved."))
                st.rerun()

    # ------------------------------------------------------------ 4. compare
    st.subheader(t("4. Compare and choose"))
    rows = []
    for s in sups:
        if not s.get("unit_price_usd") or s["status"] == "Rejected":
            continue
        e = quote_economics(product, s, ctx.settings)
        rows.append({"id": s["id"], "Supplier": s["name"], "Status": s["status"], "Price $": s["unit_price_usd"],
                     "MOQ": s.get("moq"), "Lead time (d)": s.get("lead_time_days"),
                     "Landed cost £": e.landed_cost, "Profit £/unit": e.profit, "Margin %": e.margin * 100,
                     "Verdict": e.band, "First order £": e.first_order_cash})
    if not rows:
        st.caption(t("No prices yet."))
    else:
        cmp = pd.DataFrame(rows).sort_values("Profit £/unit", ascending=False)
        st.caption(t("When selling at {price} (change it in Products & margins).",
                     price=ui.gbp(product["sale_price"])))
        shown = cmp.drop(columns=["id"]).assign(Verdict=cmp["Verdict"].map(t))
        table(shown, status_cols=["Status"], column_config={
            "Price $": st.column_config.NumberColumn(format="$%.2f"),
            "Landed cost £": st.column_config.NumberColumn(format="£%.2f"),
            "Profit £/unit": st.column_config.NumberColumn(format="£%.2f"),
            "Margin %": st.column_config.NumberColumn(format="%.1f%%"),
            "First order £": st.column_config.NumberColumn(format="£%.2f")})
        c1, c2 = st.columns([3, 1])
        best = int(cmp.iloc[0]["id"])
        pick = c1.selectbox(t("Quote to choose"), cmp["id"].tolist(), index=0,
                            format_func=lambda i: by_id[i]["name"] + (" " + t("(most profitable)") if i == best else ""))
        if c2.button(t("Choose this quote"), type="primary"):
            s = by_id[pick]
            for other in sups:
                if other["status"] == "Selected" and other["id"] != pick:
                    db.update("suppliers", int(other["id"]), {"status": "Quote received"})
            db.update("suppliers", int(pick), {"status": "Selected"})
            vals = {"unit_cost_usd": s["unit_price_usd"]}
            if s.get("moq"):
                vals["first_order_qty"] = int(s["moq"])
            if s.get("shipping_usd") and s.get("moq"):
                vals["freight_per_unit"] = round(float(s["shipping_usd"]) / float(s["moq"]) / ctx.fx, 4)
            db.update("products", pid, vals)
            ui.bump()
            ui.flash(t("Quote from {name} chosen. Next step: create the purchase order.", name=s["name"]))
            st.switch_page(ui.PAGES["Purchases & payments"])

    # ------------------------------------------------------------ history
    hist = db.read("messages")
    hist = hist[hist["product_id"] == pid]
    with st.expander(t("Message history ({n})", n=len(hist))):
        if hist.empty:
            st.caption(t("No messages sent yet."))
        else:
            hist = hist.assign(Supplier=hist["supplier_id"].map(lambda i: by_id.get(i, {}).get("name")))
            table(hist[["sent_at", "Supplier", "channel", "to_address", "subject", "status"]]
                  .rename(columns={"sent_at": "Date", "channel": "Channel", "to_address": "To",
                                   "subject": "Subject", "status": "Status"})
                  .sort_values("Date", ascending=False))
