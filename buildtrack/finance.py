"""Budget roll-up calculations."""

from __future__ import annotations

import pandas as pd

from buildtrack import db


def budget_summary(project_id: int) -> pd.DataFrame:
    """One row per budget line with change orders rolled in.

    Revised Budget = Original Budget + Approved COs
    Projected Cost = max(Committed, Actual)
    Over/Under     = Revised Budget - Projected Cost  (negative = over budget)
    """
    lines = db.list_records("budget_lines", project_id, order_by="cost_code")
    cos = db.list_records("change_orders", project_id)
    if lines.empty:
        return pd.DataFrame(columns=["id", "cost_code", "description", "Original Budget", "Approved COs",
                                     "Pending COs", "Revised Budget", "Committed", "Actual",
                                     "Projected Cost", "Over/Under"])

    def co_total(status: str) -> pd.Series:
        sub = cos[cos["status"] == status] if not cos.empty else cos
        return sub.groupby("cost_code")["amount"].sum() if not sub.empty else pd.Series(dtype=float)

    approved, pending = co_total("Approved"), co_total("Pending")
    out = pd.DataFrame({
        "id": lines["id"],
        "cost_code": lines["cost_code"],
        "description": lines["description"],
        "Original Budget": lines["original_budget"].fillna(0),
    })
    out["Approved COs"] = lines["cost_code"].map(approved).fillna(0)
    out["Pending COs"] = lines["cost_code"].map(pending).fillna(0)
    out["Revised Budget"] = out["Original Budget"] + out["Approved COs"]
    out["Committed"] = lines["committed"].fillna(0)
    out["Actual"] = lines["actual"].fillna(0)
    out["Projected Cost"] = out[["Committed", "Actual"]].max(axis=1)
    out["Over/Under"] = out["Revised Budget"] - out["Projected Cost"]
    return out


def unmatched_change_orders(project_id: int) -> pd.DataFrame:
    """Change orders whose cost code doesn't match any budget line."""
    lines = db.list_records("budget_lines", project_id)
    cos = db.list_records("change_orders", project_id)
    if cos.empty:
        return cos
    return cos[~cos["cost_code"].isin(lines["cost_code"])]
