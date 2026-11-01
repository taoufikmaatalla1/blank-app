import datetime as dt

import pandas as pd
import streamlit as st

from buildtrack import charts, db
from buildtrack.finance import budget_summary
from buildtrack.tools import CHANGE_ORDERS, PUNCH, RFIS, SUBMITTALS
from buildtrack.ui import (STATUS_COLORS, is_overdue, money, page_header, parse_date, require_project,
                           short_money, show_flash, status_badge)

show_flash()
project = require_project()
pid = project["id"]
page_header(project["name"], "🏗️", subtitle=f"{project['number'] or ''} · {project.get('address') or ''}")

# ----------------------------------------------------------------------------- project header
today = dt.date.today()
start, end = parse_date(project.get("start_date")), parse_date(project.get("end_date"))
with st.container(border=True):
    a, b, c, d = st.columns([1.2, 1, 1, 2], vertical_alignment="center")
    with a:
        status_badge(project.get("status"))
        st.caption(f"Client: **{project.get('client') or '—'}**  \nPM: **{project.get('project_manager') or '—'}**")
    b.markdown(f"**Start**  \n{start:%b %d, %Y}" if start else "**Start**  \n—")
    c.markdown(f"**Completion**  \n{end:%b %d, %Y}" if end else "**Completion**  \n—")
    with d:
        if start and end and end > start:
            elapsed = min(1.0, max(0.0, (today - start).days / (end - start).days))
            remaining = (end - today).days
            label = f"{remaining} days remaining" if remaining >= 0 else f"{-remaining} days past completion"
            st.progress(elapsed, text=f"Time elapsed: {elapsed:.0%} · {label}")
        if project.get("description"):
            st.caption(project["description"])

# ----------------------------------------------------------------------------- KPIs
rfis = db.list_records("rfis", pid)
subs = db.list_records("submittals", pid)
punch = db.list_records("punch_items", pid)
cos = db.list_records("change_orders", pid)
tasks = db.list_records("schedule_tasks", pid)
budget = budget_summary(pid)

rfi_overdue, sub_overdue = is_overdue(RFIS, rfis), is_overdue(SUBMITTALS, subs)
punch_overdue, co_overdue = is_overdue(PUNCH, punch), is_overdue(CHANGE_ORDERS, cos)

open_rfis = int((~rfis["status"].isin(RFIS.closed_statuses)).sum()) if not rfis.empty else 0
open_subs = int((~subs["status"].isin(SUBMITTALS.closed_statuses)).sum()) if not subs.empty else 0
open_punch = int((punch["status"] != "Closed").sum()) if not punch.empty else 0
if not tasks.empty:
    s = pd.to_datetime(tasks["start_date"], errors="coerce")
    e = pd.to_datetime(tasks["end_date"], errors="coerce")
    dur = (e - s).dt.days.clip(lower=1)
    sched_pct = float((tasks["percent_complete"].fillna(0) * dur).sum() / dur.sum())
else:
    sched_pct = 0.0
over_under = float(budget["Over/Under"].sum()) if not budget.empty else 0.0
pending_cos = float(cos.loc[cos["status"] == "Pending", "amount"].sum()) if not cos.empty else 0.0

k = st.columns(6)
k[0].metric("Open RFIs", open_rfis, f"{int(rfi_overdue.sum())} overdue", delta_color="inverse", delta_arrow="off", border=True)
k[1].metric("Open submittals", open_subs, f"{int(sub_overdue.sum())} overdue", delta_color="inverse", delta_arrow="off", border=True)
k[2].metric("Open punch items", open_punch, f"{int(punch_overdue.sum())} overdue", delta_color="inverse", delta_arrow="off",
            border=True)
k[3].metric("Schedule complete", f"{sched_pct:.0f}%", border=True)
k[4].metric("Pending COs", short_money(pending_cos), f"{int((cos['status'] == 'Pending').sum()) if not cos.empty else 0} awaiting decision",
            delta_color="off", delta_arrow="off", border=True)
k[5].metric("Budget over/under", short_money(over_under), "under" if over_under >= 0 else "over",
            delta_color="normal" if over_under >= 0 else "inverse", delta_arrow="off", border=True)

# ----------------------------------------------------------------------------- charts + action items
left, right = st.columns([3, 2])

with left:
    with st.container(border=True):
        st.markdown("**Status breakdown**")
        t1, t2, t3 = st.tabs(["RFIs", "Submittals", "Punch list"])
        for tab, df, label in ((t1, rfis, "RFIs"), (t2, subs, "Submittals"), (t3, punch, "Punch items")):
            with tab:
                if df.empty:
                    st.caption(f"No {label.lower()} yet.")
                else:
                    st.altair_chart(charts.status_bar(df, "status", "", STATUS_COLORS), width="stretch")
    if not budget.empty:
        with st.container(border=True):
            st.markdown("**Budget by cost code**")
            st.altair_chart(charts.budget_bars(budget), width="stretch")

with right:
    with st.container(border=True):
        st.markdown("**⚠️ Overdue action items**")
        items = []
        for df, mask, prefix, title_col, owner_col, page in (
            (rfis, rfi_overdue, "RFI", "subject", "assigned_to", "views/rfis.py"),
            (subs, sub_overdue, "SUB", "title", "reviewer", "views/submittals.py"),
            (punch, punch_overdue, "PL", "title", "assigned_to", "views/punch_list.py"),
            (cos, co_overdue, "CO", "title", None, "views/change_orders.py"),
        ):
            for _, r in df[mask].iterrows():
                due = parse_date(r["due_date"])
                items.append(dict(ref=f"{prefix}-{int(r['number']):03d}", title=r[title_col],
                                  owner=r[owner_col] if owner_col else "", due=due,
                                  days=(today - due).days if due else 0, page=page))
        if not items:
            st.success("Nothing overdue. Nice work!", icon="🎉")
        else:
            items.sort(key=lambda x: -x["days"])
            for it in items[:10]:
                c1, c2 = st.columns([4, 1], vertical_alignment="center")
                c1.markdown(f"**{it['ref']}** {it['title']}  \n"
                            f":gray[{it['owner'] or 'Unassigned'} · due {it['due']:%b %d}]")
                c2.markdown(f":red[**{it['days']}d late**]")
            if len(items) > 10:
                st.caption(f"+ {len(items) - 10} more")

    with st.container(border=True):
        st.markdown("**📓 Latest daily log**")
        log = db.fetch_one("SELECT * FROM daily_logs WHERE project_id = ? ORDER BY log_date DESC LIMIT 1", (pid,))
        if not log:
            st.caption("No daily logs yet.")
        else:
            ld = parse_date(log["log_date"])
            st.markdown(f"**{ld:%A, %b %d}** · {log['weather'] or '—'} {log['temp_high'] or ''}°F · "
                        f"👷 {log['workers'] or 0} workers")
            st.write(log["work_performed"] or "")
            if log.get("delays"):
                st.warning(log["delays"], icon="⏱️")

    with st.container(border=True):
        st.markdown("**📅 Upcoming (next 30 days)**")
        if tasks.empty:
            st.caption("No schedule tasks yet.")
        else:
            s = pd.to_datetime(tasks["start_date"], errors="coerce").dt.date
            soon = tasks[(s >= today) & (s <= today + dt.timedelta(days=30))].sort_values("start_date")
            if soon.empty:
                st.caption("Nothing starting in the next 30 days.")
            for _, t in soon.head(6).iterrows():
                icon = "◆" if t["milestone"] else "▸"
                st.markdown(f"{icon} **{t['name']}** :gray[· {parse_date(t['start_date']):%b %d}]")

# ----------------------------------------------------------------------------- portfolio
st.subheader("Portfolio")
portfolio = db.query_df("""
    SELECT p.id, p.number, p.name, p.status, p.contract_value, p.end_date,
        (SELECT COUNT(*) FROM rfis r WHERE r.project_id = p.id AND r.status NOT IN ('Answered','Closed')) AS open_rfis,
        (SELECT COUNT(*) FROM punch_items i WHERE i.project_id = p.id AND i.status != 'Closed') AS open_punch,
        (SELECT COALESCE(SUM(amount),0) FROM change_orders c WHERE c.project_id = p.id AND c.status = 'Approved') AS approved_cos
    FROM projects p ORDER BY p.number
""")
portfolio["end_date"] = pd.to_datetime(portfolio["end_date"], errors="coerce")
st.dataframe(
    portfolio.drop(columns=["id"]),
    hide_index=True,
    width="stretch",
    column_config={
        "number": "Project #", "name": "Project", "status": "Status",
        "contract_value": st.column_config.NumberColumn("Contract value", format="dollar"),
        "end_date": st.column_config.DateColumn("Completion", format="MMM D, YYYY"),
        "open_rfis": "Open RFIs", "open_punch": "Open punch",
        "approved_cos": st.column_config.NumberColumn("Approved COs", format="dollar"),
    },
)
st.caption(f"Total contract value across portfolio: **{money(portfolio['contract_value'].sum())}**")
