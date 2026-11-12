"""Unit economics for an Amazon product sourced from Alibaba.

All money is in GBP unless the field name says otherwise. The functions are
pure so they can be tested without Streamlit or the database.
"""

from __future__ import annotations

from dataclasses import dataclass

MIN_REFERRAL_FEE = 0.25  # Amazon minimum referral fee per item (GBP)


@dataclass(frozen=True)
class Economics:
    price: float
    vat: float
    referral_fee: float
    fba_fee: float
    product_cost: float
    freight: float
    duty: float
    landed_cost: float
    ads: float
    other: float
    profit: float
    margin: float
    roi: float
    breakeven_acos: float
    first_order_cash: float
    band: str


def margin_band(margin: float) -> str:
    """Classify a net margin the same way as the PDF dashboard."""
    if margin < 0.10:
        return "Too low"
    if margin < 0.20:
        return "Thin"
    return "Solid"


def unit_economics(product: dict, settings: dict) -> Economics:
    price = float(product.get("sale_price") or 0)
    fx = float(settings.get("usd_per_gbp") or 1.27)
    vat_rate = float(settings.get("vat_rate") or 0) if settings.get("vat_registered", True) else 0.0

    vat = price - price / (1 + vat_rate) if vat_rate else 0.0
    referral = max(price * float(product.get("referral_pct") or 0), MIN_REFERRAL_FEE) if price else 0.0
    fba = float(product.get("fba_fee") or 0)
    cost = float(product.get("unit_cost_usd") or 0) / fx
    freight = float(product.get("freight_per_unit") or 0)
    duty = cost * float(product.get("duty_pct") or 0)
    landed = cost + freight + duty
    ads = price * float(product.get("ads_pct") or 0)
    other = float(product.get("other_per_unit") or 0)

    profit = price - vat - referral - fba - landed - ads - other
    margin = profit / price if price else 0.0
    roi = profit / landed if landed else 0.0
    # ACoS at which the product only breaks even (profit before ads / price).
    breakeven_acos = (profit + ads) / price if price else 0.0
    qty = int(product.get("first_order_qty") or 0)
    first_order = qty * landed + float(product.get("first_order_fixed") or 0)

    return Economics(
        price=price, vat=vat, referral_fee=referral, fba_fee=fba, product_cost=cost,
        freight=freight, duty=duty, landed_cost=landed, ads=ads, other=other,
        profit=profit, margin=margin, roi=roi, breakeven_acos=breakeven_acos,
        first_order_cash=first_order, band=margin_band(margin),
    )


def price_for_margin(product: dict, settings: dict, target_margin: float) -> float:
    """Sale price needed to reach a target net margin (solved numerically)."""
    lo, hi = 0.5, 500.0
    for _ in range(60):
        mid = (lo + hi) / 2
        m = unit_economics({**product, "sale_price": mid}, settings).margin
        if m < target_margin:
            lo = mid
        else:
            hi = mid
    return round(hi, 2)


def ads_forecast(daily_budget: float, cpc: float, conversion_rate: float, price: float) -> dict:
    clicks = daily_budget / cpc if cpc else 0.0
    orders = clicks * conversion_rate
    sales = orders * price
    acos = daily_budget / sales if sales else 0.0
    return {"clicks": clicks, "orders": orders, "sales": sales, "acos": acos}
