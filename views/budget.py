import pandas as pd
import streamlit as st

from buildtrack import charts, db
from buildtrack.finance import budget_summary, unmatched_change_orders
from buildtrack.ui import flash, money, page_header, require_project, short_money, show_flash

show_flash()
project = require_project()
pid = project["id"]
page_header("Budget", "💰", project)

summary = budget_summary(pid)
totals = summary.select_dtypes("number").drop(columns=["id"]).sum()

contract = float(project.get("contract_value") or 0)
c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Contract value", short_money(contract), border=True)
c2.metric("Original budget", short_money(totals.get("Original Budget", 0)), border=True)
c3.metric("Revised budget", short_money(totals.get("Revised Budget", 0)),
          f"{short_money(totals.get('Approved COs', 0))} approved COs", delta_color="off", delta_arrow="off", border=True)
c4.metric("Committed", short_money(totals.get("Committed", 0)),
          f"{totals.get('Committed', 0) / totals['Revised Budget'] * 100:.0f}% of revised"
          if totals.get("Revised Budget") else None, delta_color="off", delta_arrow="off", border=True)
over_under = totals.get("Over/Under", 0)
c5.metric("Projected over/under", short_money(over_under),
          "under budget" if over_under >= 0 else "over budget",
          delta_color="normal" if over_under >= 0 else "inverse", delta_arrow="off", border=True)

orphans = unmatched_change_orders(pid)
if not orphans.empty:
    st.warning(f"{len(orphans)} change order(s) use a cost code with no budget line and are not rolled up: "
               + ", ".join(sorted(orphans["cost_code"].fillna("(blank)").unique())), icon="⚠️")

summary_tab, edit_tab = st.tabs(["Budget summary", "Edit budget lines"])

with summary_tab:
    if summary.empty:
        st.info("No budget lines yet. Add them in the **Edit budget lines** tab.", icon="📭")
    else:
        st.altair_chart(charts.budget_bars(summary), width="stretch")
        display = summary.drop(columns=["id"]).rename(columns={"cost_code": "Cost code", "description": "Description"})
        total_row = pd.DataFrame([{"Cost code": "TOTAL", "Description": "", **totals.to_dict()}])
        display = pd.concat([display, total_row], ignore_index=True)
        money_cols = [c for c in display.columns if c not in ("Cost code", "Description")]
        styled = display.style.format({c: money for c in money_cols}).map(
            lambda v: "color: #DC2626; font-weight: 600" if isinstance(v, (int, float)) and v < 0 else "",
            subset=["Over/Under"],
        )
        st.dataframe(styled, hide_index=True, width="stretch", height=38 * (len(display) + 1))
        st.download_button("Export CSV", display.to_csv(index=False).encode(), "budget.csv", "text/csv",
                           icon=":material/download:")
        st.caption("Revised Budget = Original + Approved COs · Projected Cost = greater of Committed and Actual · "
                   "Over/Under = Revised − Projected (red = over budget)")

with edit_tab:
    st.caption("Edit cells directly, add rows at the bottom, or select rows and press Delete. Then save.")
    lines = db.list_records("budget_lines", pid, order_by="cost_code")[
        ["id", "cost_code", "description", "original_budget", "committed", "actual"]]
    edited = st.data_editor(
        lines,
        num_rows="dynamic",
        hide_index=True,
        width="stretch",
        key=f"budget_editor_{pid}",
        column_config={
            "id": None,
            "cost_code": st.column_config.TextColumn("Cost code", required=True),
            "description": st.column_config.TextColumn("Description", width="large"),
            "original_budget": st.column_config.NumberColumn("Original budget", format="dollar", min_value=0),
            "committed": st.column_config.NumberColumn("Committed", format="dollar", min_value=0),
            "actual": st.column_config.NumberColumn("Actual cost", format="dollar", min_value=0),
        },
    )
    if st.button("Save budget", type="primary", icon=":material/save:"):
        original_ids = set(lines["id"].dropna().astype(int))
        kept_ids = set()
        for row in edited.to_dict("records"):
            if not row.get("cost_code"):
                continue
            data = {k: (0 if k in ("original_budget", "committed", "actual") and pd.isna(v) else v)
                    for k, v in row.items() if k != "id"}
            if pd.notna(row.get("id")):
                rid = int(row["id"])
                kept_ids.add(rid)
                db.update("budget_lines", rid, data)
            else:
                db.insert("budget_lines", {**data, "project_id": pid})
        for rid in original_ids - kept_ids:
            db.delete("budget_lines", rid)
        st.session_state.pop(f"budget_editor_{pid}", None)
        flash("Budget saved")
        st.rerun()
