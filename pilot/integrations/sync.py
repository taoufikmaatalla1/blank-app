"""Operations shared by the Streamlit app and the REST API."""

from __future__ import annotations

from .. import db
from .amazon import AmazonClient


def sync_amazon_fees(client: AmazonClient) -> dict:
    """Replace estimated fees with Amazon's own estimate for every product that has an ASIN."""
    updated, skipped = [], []
    for p in db.records("products"):
        if not p.get("asin"):
            skipped.append(p["name"])
            continue
        est = client.fees_estimate(p["asin"], float(p["sale_price"]))
        vals = {"fba_fee": round(est["fba"], 2)}
        if est["referral"]:
            vals["referral_pct"] = round(est["referral"] / float(p["sale_price"]), 4)
        db.update("products", int(p["id"]), vals)
        updated.append({"product": p["name"], **vals})
    return {"updated": updated, "skipped_no_asin": skipped}
