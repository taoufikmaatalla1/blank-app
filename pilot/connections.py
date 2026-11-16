"""Connections page: status and setup of the Amazon, Alibaba and Gmail connections."""

from __future__ import annotations

import os

import streamlit as st

from . import db, ui
from .integrations import AlibabaClient, AlibabaError, AmazonClient, AmazonError, factory, mailer
from .integrations import oauth_state, sync
from .i18n import lang, t

AMAZON_SETUP = """
1. In Seller Central: **Apps and Services → Develop Apps**, register as a developer (*private
   developer*) and create an app (*SP API*).
2. Under *LWA credentials*, click **View**: note the *Client identifier* and *Client secret*.
3. **Authorize → Generate refresh token**: note the `Atzr|...` key.
4. In Streamlit (**⋮ → Settings → Secrets**), add:
   `AMAZON_LWA_CLIENT_ID`, `AMAZON_LWA_CLIENT_SECRET`, `AMAZON_REFRESH_TOKEN`,
   `AMAZON_SELLER_ID` (Merchant Token: Settings → Account Info → Business Information).
5. While your Amazon app is a Sandbox app, also add `AMAZON_SANDBOX = "1"`.
"""

ALIBABA_SETUP = """
1. Create a **buyer** account at [openapi.alibaba.com](https://openapi.alibaba.com/) with a country
   **outside mainland China**.
2. In the [App Console](https://openapi.alibaba.com/app/index.htm), create an **ISV-Dropshipping**
   app with this app's address as the *Callback URL*.
3. Request the **SystemAPI** and **ICBU Dropshipping Solution Api Group** permission groups.
4. In Streamlit Secrets: `ALIBABA_APP_KEY`, `ALIBABA_APP_SECRET`, `ALIBABA_REDIRECT_URI`
   (exactly the same address as the *Callback URL*).
"""

GMAIL_SETUP = """
To send quote requests to suppliers from your Gmail:
1. Turn on **2-Step Verification** on your Google account.
2. Go to **myaccount.google.com → Security → App passwords** and create a password for
   "TASOH Seller" (16 characters).
3. In Streamlit Secrets, add `GMAIL_ADDRESS = "you@gmail.com"` and
   `GMAIL_APP_PASSWORD = "xxxx xxxx xxxx xxxx"`.
"""

AMAZON_SETUP_FR = """
1. Dans Seller Central : **Apps and Services → Develop Apps**, inscrivez-vous comme développeur
   (*private developer*) et créez une application (*SP API*).
2. Sous *LWA credentials*, cliquez sur **View** : notez le *Client identifier* et le *Client secret*.
3. **Authorize → Generate refresh token** : notez la clé `Atzr|...`.
4. Dans Streamlit (**⋮ → Settings → Secrets**), ajoutez :
   `AMAZON_LWA_CLIENT_ID`, `AMAZON_LWA_CLIENT_SECRET`, `AMAZON_REFRESH_TOKEN`,
   `AMAZON_SELLER_ID` (Merchant Token : Settings → Account Info → Business Information).
5. Tant que votre application Amazon est en Sandbox, ajoutez aussi `AMAZON_SANDBOX = "1"`.
"""

ALIBABA_SETUP_FR = """
1. Créez un compte **acheteur** sur [openapi.alibaba.com](https://openapi.alibaba.com/) avec un pays
   **hors Chine continentale**.
2. Dans l'[App Console](https://openapi.alibaba.com/app/index.htm), créez une application
   **ISV-Dropshipping** avec l'adresse de cette application comme *Callback URL*.
3. Demandez les permissions **SystemAPI** et **ICBU Dropshipping Solution Api Group**.
4. Dans les Secrets Streamlit : `ALIBABA_APP_KEY`, `ALIBABA_APP_SECRET`, `ALIBABA_REDIRECT_URI`
   (exactement la même adresse que la *Callback URL*).
"""

GMAIL_SETUP_FR = """
Pour envoyer les demandes de prix aux fournisseurs depuis votre Gmail :
1. Activez la **validation en deux étapes** sur votre compte Google.
2. Allez sur **myaccount.google.com → Sécurité → Mots de passe des applications** et créez un mot
   de passe pour « TASOH Seller » (16 caractères).
3. Dans les Secrets Streamlit, ajoutez `GMAIL_ADDRESS = "vous@gmail.com"` et
   `GMAIL_APP_PASSWORD = "xxxx xxxx xxxx xxxx"`.
"""


def _setup(en: str, fr: str) -> str:
    return fr if lang() == "fr" else en


def show_error(e: Exception) -> None:
    st.error(str(e))
    details = getattr(e, "details", None)
    if details:
        with st.expander(t("Details")):
            st.json(details)


def alibaba_ready() -> bool:
    return AlibabaClient.configured() and bool(factory.alibaba_token_info())


def handle_alibaba_callback() -> None:
    """If Alibaba came back here with ?code=..., exchange the code for access tokens."""
    qp = st.query_params
    if "code" not in qp or not AlibabaClient.configured():
        return
    code, state = qp.get("code"), qp.get("state", "")
    st.query_params.clear()
    if not oauth_state.accept(state):
        st.warning(t("This Alibaba authorization has expired or did not start from this app. Click "
                   "**Connect my Alibaba buyer account** again (Connections page)."))
        return
    try:
        tok = factory.alibaba().create_token(code)
        oauth_state.clear()
        st.success(t("Alibaba account connected: {name}",
                     name=tok.get("user_nick") or tok.get("account") or ""))
    except AlibabaError as e:
        show_error(e)


def render() -> None:
    st.title(t("🔌 Connections"))
    st.caption(t("Your Amazon seller, Alibaba buyer and Gmail accounts. Anything that changes Amazon "
               "or Alibaba asks you to confirm first; payments always happen on Alibaba/PayPal, by you."))
    amazon_ok, alibaba_ok, token = (AmazonClient.configured(), AlibabaClient.configured(),
                                    factory.alibaba_token_info())
    c1, c2, c3 = st.columns(3)
    c1.metric(t("Amazon Seller"), t("Keys saved") if amazon_ok else t("Not set up"))
    c2.metric(t("Alibaba.com"), t("Connected") if token else t("App set up, not authorized"
                                                        if alibaba_ok else "Not set up"))
    c3.metric(t("Gmail"), t("Set up") if mailer.configured() else t("Not set up"))

    t_amz, t_ali, t_mail = st.tabs([t("Amazon"), t("Alibaba"), t("Gmail")])
    with t_amz:
        _amazon(amazon_ok)
    with t_ali:
        _alibaba(alibaba_ok, token)
    with t_mail:
        if mailer.configured():
            st.success(t("E-mails are sent from {sender}.", sender=mailer.sender()))
        else:
            st.info(t("Gmail is not set up."))
        st.markdown(_setup(GMAIL_SETUP, GMAIL_SETUP_FR))


def _amazon(ok: bool) -> None:
    if not ok:
        st.info(t("Amazon is not connected yet."))
        st.markdown(_setup(AMAZON_SETUP, AMAZON_SETUP_FR))
        return
    try:
        client = factory.amazon()
    except AmazonError as e:
        show_error(e)
        return
    if os.environ.get("AMAZON_SANDBOX", "") in ("1", "true", "yes"):
        st.info(t("**Sandbox** mode: Amazon returns test data, not yours."))
    a, b = st.columns(2)
    if a.button(t("Test connection")):
        try:
            parts = client.marketplace_participations()
            names = [p.get("marketplace", {}).get("name") for p in parts]
            st.success(t("Connected.") + (" " + t("Marketplaces: {names}", names=", ".join(n for n in names if n))
                                          if any(names) else ""))
        except AmazonError as e:
            show_error(e)
    if b.button(t("Update fees from Amazon"),
                help=t("Uses Amazon's fee estimate for each product that has an ASIN")):
        try:
            res = sync.sync_amazon_fees(client)
            st.success(t("Updated {n} product(s).", n=len(res["updated"])))
            if res["skipped_no_asin"]:
                st.caption(t("No ASIN yet:") + " " + ", ".join(res["skipped_no_asin"]))
        except AmazonError as e:
            show_error(e)


def _alibaba(ok: bool, token: dict) -> None:
    if not ok:
        st.info(t("Alibaba is not set up yet."))
        st.markdown(_setup(ALIBABA_SETUP, ALIBABA_SETUP_FR))
        return
    try:
        client = factory.alibaba()
    except AlibabaError as e:
        show_error(e)
        return
    if token:
        st.success(t("Connected as {name}", name=token.get("user_nick") or token.get("account") or t("buyer")))
        if st.button(t("Refresh access token")):
            try:
                client.refresh()
                st.success(t("Access refreshed."))
            except AlibabaError as e:
                show_error(e)
    else:
        st.link_button(t("Connect my Alibaba buyer account ↗"), client.authorize_url(oauth_state.start()))
        st.caption(t("You sign in on Alibaba and come back here automatically. The SystemAPI and ICBU "
                   "Dropshipping permission groups must be \"Active\" in the App Console."))

    st.markdown(t("**Events received from Alibaba** (price changes, order status)"))
    ev = db.events()
    if ev.empty:
        st.caption(t("None yet. They arrive through the REST API (/alibaba/webhook)."))
    else:
        st.dataframe(ev, hide_index=True, width="stretch")
    ui.link("Product search", t("Search products on Alibaba →"), "🔎")
