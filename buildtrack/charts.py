"""Altair charts used across pages."""

from __future__ import annotations

import datetime as dt

import altair as alt
import pandas as pd

ORANGE = "#F47E20"
PHASE_COLORS = {
    "Pre-Construction": "#8A94A6",
    "Sitework": "#A0703C",
    "Structure": "#F47E20",
    "Envelope": "#2E86AB",
    "Interiors": "#7B61FF",
    "Closeout": "#2BA84A",
}


def gantt(tasks: pd.DataFrame) -> alt.LayerChart:
    df = tasks.copy()
    df["start"] = pd.to_datetime(df["start_date"], errors="coerce")
    df["end"] = pd.to_datetime(df["end_date"], errors="coerce")
    df = df.dropna(subset=["start", "end"])
    df["milestone"] = df["milestone"].fillna(0).astype(bool)
    duration = (df["end"] - df["start"]).dt.days.clip(lower=0)
    df["progress_end"] = df["start"] + pd.to_timedelta(duration * df["percent_complete"].fillna(0) / 100, unit="D")
    df["label"] = df["name"]
    df = df.sort_values(["start", "id"])
    order = df["label"].tolist()

    y = alt.Y("label:N", sort=order, title=None, axis=alt.Axis(labelLimit=220))
    phases = [p for p in PHASE_COLORS if p in set(df["phase"])] + sorted(set(df["phase"].dropna()) - set(PHASE_COLORS))
    color = alt.Color("phase:N", title="Phase",
                      scale=alt.Scale(domain=phases, range=[PHASE_COLORS.get(p, "#999") for p in phases]),
                      legend=alt.Legend(orient="top"))
    tooltip = [
        alt.Tooltip("name:N", title="Task"), alt.Tooltip("phase:N", title="Phase"),
        alt.Tooltip("trade:N", title="Trade"),
        alt.Tooltip("start:T", title="Start", format="%b %d, %Y"),
        alt.Tooltip("end:T", title="Finish", format="%b %d, %Y"),
        alt.Tooltip("percent_complete:Q", title="% complete"),
    ]
    bars = df[~df["milestone"]]
    base = alt.Chart(bars).encode(y=y)
    planned = base.mark_bar(opacity=0.35, cornerRadius=3, height=16).encode(
        x=alt.X("start:T", title=None, axis=alt.Axis(format="%b %Y", grid=True)), x2="end:T",
        color=color, tooltip=tooltip)
    done = base.mark_bar(cornerRadius=3, height=16).encode(x="start:T", x2="progress_end:T", color=color,
                                                           tooltip=tooltip)
    milestones = alt.Chart(df[df["milestone"]]).mark_point(shape="diamond", size=180, filled=True,
                                                           color="#1F2937").encode(
        x="start:T", y=y, tooltip=tooltip)
    today = alt.Chart(pd.DataFrame({"today": [pd.Timestamp(dt.date.today())]})).mark_rule(
        color="#E11D48", strokeDash=[4, 4], size=2).encode(x="today:T")
    return (planned + done + milestones + today).properties(height=max(220, 28 * len(df)))


def manpower(logs: pd.DataFrame) -> alt.Chart:
    df = logs.copy()
    df["date"] = pd.to_datetime(df["log_date"], errors="coerce")
    return alt.Chart(df).mark_bar(color=ORANGE, cornerRadiusTopLeft=3, cornerRadiusTopRight=3).encode(
        x=alt.X("yearmonthdate(date):T", title=None, axis=alt.Axis(format="%b %d")),
        y=alt.Y("workers:Q", title="Workers on site"),
        tooltip=[alt.Tooltip("date:T", format="%a %b %d"), "workers:Q", "weather:N", "hours:Q"],
    ).properties(height=220)


def status_bar(df: pd.DataFrame, field: str, title: str, color_map: dict[str, str]) -> alt.Chart:
    counts = df[field].fillna("—").value_counts().rename_axis("status").reset_index(name="count")
    domain = counts["status"].tolist()
    palette = {"gray": "#9CA3AF", "blue": "#3B82F6", "violet": "#8B5CF6", "green": "#22C55E",
               "orange": ORANGE, "red": "#EF4444"}
    rng = [palette.get(color_map.get(s, "gray"), "#9CA3AF") for s in domain]
    return alt.Chart(counts, title=title).mark_bar(cornerRadiusEnd=4).encode(
        x=alt.X("count:Q", title=None, axis=alt.Axis(tickMinStep=1)),
        y=alt.Y("status:N", sort="-x", title=None),
        color=alt.Color("status:N", scale=alt.Scale(domain=domain, range=rng), legend=None),
        tooltip=["status:N", "count:Q"],
    ).properties(height=max(120, 32 * len(counts)))


def budget_bars(summary: pd.DataFrame) -> alt.Chart:
    long = summary.melt(id_vars=["cost_code", "description"],
                        value_vars=["Revised Budget", "Committed", "Actual"],
                        var_name="measure", value_name="amount")
    return alt.Chart(long).mark_bar(cornerRadiusTopLeft=2, cornerRadiusTopRight=2).encode(
        x=alt.X("cost_code:N", title="Cost code"),
        xOffset="measure:N",
        y=alt.Y("amount:Q", title=None, axis=alt.Axis(format="$,.0s")),
        color=alt.Color("measure:N", title=None, legend=alt.Legend(orient="top"),
                        scale=alt.Scale(domain=["Revised Budget", "Committed", "Actual"],
                                        range=["#CBD5E1", "#2E86AB", ORANGE])),
        tooltip=["cost_code:N", "description:N", "measure:N", alt.Tooltip("amount:Q", format="$,.0f")],
    ).properties(height=320)
