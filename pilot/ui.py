"""Shared helpers for the Streamlit pages: styling, formatting and loading the data."""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd
import streamlit as st

from . import calc, db, pipeline

CSS = """
<style>
.eyebrow {font-family: ui-monospace, Menlo, monospace; font-size: .75rem; letter-spacing: .06em;
          text-transform: uppercase; opacity: .7;}
.eyebrow b {opacity: 1;}
.big {font-family: ui-monospace, Menlo, monospace; font-size: 2rem; font-weight: 600; line-height: 1.1;}
.sub {font-size: .85rem; opacity: .75;}
.badge {font-family: ui-monospace, Menlo, monospace; font-size: .75rem; padding: 2px 8px;
        border-radius: 4px; margin-right: 8px; white-space: nowrap;}
.b-Solid {background: rgba(46,160,67,.15); color: #2ea043;}
.b-Thin {background: rgba(210,153,34,.15); color: #b7791f;}
.b-Too {background: rgba(218,54,51,.15); color: #da3633;}
.b-stage {background: rgba(56,139,253,.15); color: #2f81f7;}
</style>
"""

# Filled by streamlit_app.py: page title -> st.Page, so pages can link to each other.
PAGES: dict = {}


def gbp(x: float | None) -> str:
    x = 0.0 if x is None or pd.isna(x) or abs(x) < 0.005 else x  # avoid "£-0.00"
    return f"£{x:,.2f}"


def usd(x: float | None) -> str:
    return "–" if x is None or pd.isna(x) else f"${x:,.2f}"


def badge(band: str, margin: float) -> str:
    from .i18n import t
    return f'<span class="badge b-{band.split()[0]}">{t(band)} · {margin * 100:.1f} %</span>'


def stage_badge(stage: str) -> str:
    from .i18n import t
    return f'<span class="badge b-stage">{t(stage)}</span>'


def ver() -> int:
    return st.session_state.setdefault("ver", 0)


def bump() -> None:
    """Force data editors to re-read the database after a save."""
    st.session_state.ver = ver() + 1


def link(page_title: str, label: str | None = None, icon: str | None = None) -> None:
    """Link to a page by its English title; the label is shown in the current language."""
    from .i18n import t
    page = PAGES.get(page_title)
    if page is not None:
        st.page_link(page, label=label or t(page_title), icon=icon)


def flash(message: str, kind: str = "success") -> None:
    """Show a message after the next rerun (st.rerun() would otherwise hide it)."""
    st.session_state["_flash"] = (kind, message)


def show_flash() -> None:
    item = st.session_state.pop("_flash", None)
    if item:
        getattr(st, item[0])(item[1])


@dataclass
class Ctx:
    settings: dict
    products: list[dict]
    suppliers: pd.DataFrame
    orders: pd.DataFrame
    listings: pd.DataFrame
    checklist: pd.DataFrame
    econ: dict = field(default_factory=dict)

    @property
    def fx(self) -> float:
        return float(self.settings["usd_per_gbp"])

    @property
    def prod_by_id(self) -> dict:
        return {p["id"]: p for p in self.products}

    @property
    def prod_names(self) -> dict:
        return {p["id"]: p["name"] for p in self.products}

    def records(self, df: pd.DataFrame) -> list[dict]:
        """Rows as dicts with empty cells as None (a float column would otherwise keep NaN,
        which is truthy: an empty e-mail would look like an address)."""
        return df.astype(object).where(df.notna(), None).to_dict("records")

    def stage(self, pid: int) -> str:
        return pipeline.stage(pid, self.records(self.suppliers), self.records(self.orders),
                              self.records(self.listings))

    def next_action(self, pid: int) -> tuple[str, str]:
        return pipeline.next_action(pid, self.records(self.suppliers), self.records(self.orders),
                                    self.records(self.listings))

    def order_total_gbp(self, row) -> float:
        qty = row.get("qty") or 0
        price = row.get("unit_price_usd") or 0
        ship = row.get("shipping_usd") or 0
        qty, price, ship = (0 if pd.isna(v) else v for v in (qty, price, ship))
        return (qty * price + ship) / self.fx


def load() -> Ctx:
    settings = db.get_settings()
    products = db.records("products")
    ctx = Ctx(settings=settings, products=products, suppliers=db.read("suppliers"),
              orders=db.read("orders"), listings=db.read("listings"),
              checklist=db.read("checklist").sort_values("sort"))
    ctx.econ = {p["id"]: calc.unit_economics(p, settings) for p in products}
    return ctx


def research_defaults(settings: dict) -> dict:
    """Default assumptions to estimate the margin of a product found in search."""
    return {
        "fba_fee": float(settings.get("default_fba_fee", 3.0)),
        "referral_pct": float(settings.get("default_referral_pct", 0.15)),
        "freight_per_unit": float(settings.get("default_freight_per_unit", 0.5)),
        "duty_pct": float(settings.get("default_duty_pct", 0.04)),
        "ads_pct": float(settings.get("default_ads_pct", 0.10)),
        "other_per_unit": float(settings.get("default_other_per_unit", 0.10)),
        "first_order_fixed": 30.0,
    }
