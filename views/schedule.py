import datetime as dt

import pandas as pd
import streamlit as st

from buildtrack import charts
from buildtrack.tools import SCHEDULE
from buildtrack.ui import render_tool


def gantt_section(df: pd.DataFrame) -> None:
    today = pd.Timestamp(dt.date.today())
    start = pd.to_datetime(df["start_date"], errors="coerce")
    end = pd.to_datetime(df["end_date"], errors="coerce")
    pct = df["percent_complete"].fillna(0)
    duration = (end - start).dt.days.clip(lower=1)
    overall = float((pct * duration).sum() / duration.sum()) if duration.sum() else 0.0
    behind = int(((end < today) & (pct < 100)).sum())
    upcoming = df[(df["milestone"] == 1) & (start >= today)].sort_values("start_date")

    c1, c2, c3 = st.columns(3)
    c1.metric("Overall progress", f"{overall:.0f}%", border=True)
    c2.metric("Tasks past finish date", behind, border=True)
    if upcoming.empty:
        c3.metric("Next milestone", "—", border=True)
    else:
        m = upcoming.iloc[0]
        days = (pd.Timestamp(m["start_date"]) - today).days
        c3.metric("Next milestone", m["name"], f"in {days} days", delta_color="off", delta_arrow="off", border=True)

    with st.container(border=True):
        st.markdown("**Gantt chart** · faded bar = planned duration, solid = progress, red line = today")
        st.altair_chart(charts.gantt(df), width="stretch")


SCHEDULE.extra = gantt_section
render_tool(SCHEDULE)
