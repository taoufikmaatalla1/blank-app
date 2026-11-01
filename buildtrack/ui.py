"""Shared UI helpers and a generic "tool" page renderer.

Most construction tools (RFIs, submittals, punch list, ...) follow the same
pattern: a filterable register of records, a dialog to create one, and a detail
panel to edit or delete the selected record. ``render_tool`` implements that
pattern once, driven by a declarative ``Tool`` spec.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field
from typing import Any, Callable

import pandas as pd
import streamlit as st

from buildtrack import db

# Status -> badge colour. Anything not listed falls back to gray.
STATUS_COLORS = {
    "Draft": "gray", "Open": "blue", "Answered": "violet", "Closed": "green",
    "Submitted": "blue", "In Review": "orange", "Approved": "green",
    "Approved as Noted": "green", "Revise & Resubmit": "orange", "Rejected": "red",
    "In Progress": "orange", "Ready for Review": "violet",
    "Pending": "orange", "Active": "green", "Pre-Construction": "blue",
    "On Hold": "orange", "Complete": "gray",
}
STATUS_DOTS = {"gray": "⚪", "blue": "🔵", "violet": "🟣", "green": "🟢", "orange": "🟠", "red": "🔴"}

PRIORITIES = ["Low", "Normal", "High", "Critical"]
TRADES = [
    "General Contractor", "Sitework", "Excavation", "Concrete", "Masonry", "Structural Steel",
    "Drywall / Framing", "Roofing", "Glazing", "Openings", "Finishes", "Fire Suppression",
    "Plumbing", "HVAC / Mechanical", "Electrical", "Low Voltage", "Landscaping", "Design", "Owner",
]


# --------------------------------------------------------------------------- formatting


def money(value: Any, decimals: int = 0) -> str:
    try:
        v = float(value or 0)
    except (TypeError, ValueError):
        return "—"
    sign = "-" if v < 0 else ""
    return f"{sign}${abs(v):,.{decimals}f}"


def short_money(value: float) -> str:
    v = float(value or 0)
    sign = "-" if v < 0 else ""
    v = abs(v)
    if v >= 1_000_000:
        return f"{sign}${v / 1_000_000:.2f}M"
    if v >= 1_000:
        return f"{sign}${v / 1_000:.0f}K"
    return f"{sign}${v:,.0f}"


def status_badge(status: str | None) -> None:
    if status:
        st.badge(status, color=STATUS_COLORS.get(status, "gray"))


def status_label(status: Any) -> str:
    if not isinstance(status, str) or not status:
        return ""
    return f"{STATUS_DOTS.get(STATUS_COLORS.get(status, 'gray'), '⚪')} {status}"


def parse_date(value: Any) -> dt.date | None:
    if value in (None, "") or (isinstance(value, float) and pd.isna(value)):
        return None
    if isinstance(value, dt.datetime):
        return value.date()
    if isinstance(value, dt.date):
        return value
    try:
        return dt.date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


def flash(message: str, icon: str = "✅") -> None:
    """Queue a toast that survives the next ``st.rerun()``."""
    st.session_state["_flash"] = (message, icon)


def show_flash() -> None:
    msg = st.session_state.pop("_flash", None)
    if msg:
        st.toast(msg[0], icon=msg[1])


# --------------------------------------------------------------------------- project context


def current_project() -> dict | None:
    pid = st.session_state.get("project_id")
    return db.get("projects", pid) if pid else None


def require_project() -> dict:
    project = current_project()
    if not project:
        st.info("Create a project on the **Projects** page to get started.", icon="🏗️")
        st.stop()
    return project


def page_header(title: str, icon: str, project: dict | None = None, subtitle: str | None = None):
    """Render a page title and return the right-hand column for action buttons."""
    left, right = st.columns([3, 1], vertical_alignment="bottom")
    with left:
        st.title(f"{icon} {title}")
        caption = subtitle or (f"{project['number']} · {project['name']}" if project else None)
        if caption:
            st.caption(caption)
    return right


# --------------------------------------------------------------------------- generic tool


@dataclass
class Field:
    name: str
    label: str
    kind: str = "text"  # text | textarea | select | contact | date | int | money | percent | bool
    options: list[str] | None = None
    required: bool = False
    default: Any = None
    in_table: bool = True
    help: str | None = None


@dataclass
class Tool:
    table: str
    title: str
    singular: str
    icon: str
    fields: list[Field]
    title_field: str = "title"
    status_field: str | None = "status"
    closed_statuses: tuple[str, ...] = ()
    number_prefix: str | None = None
    project_scoped: bool = True
    order_by: str = "id DESC"
    due_field: str | None = "due_date"
    extra: Callable[[pd.DataFrame], None] | None = None
    metric_statuses: tuple[str, ...] = field(default_factory=tuple)


def _default(f: Field) -> Any:
    return f.default() if callable(f.default) else f.default


def _input(f: Field, value: Any, key: str) -> Any:
    label = f.label + (" *" if f.required else "")
    kind = f.kind
    if kind == "textarea":
        return st.text_area(label, value or "", key=key, help=f.help, height=110)
    if kind in ("select", "contact"):
        options = list(f.options or []) if kind == "select" else [""] + db.contact_names()
        if value and value not in options:
            options.append(value)
        index = options.index(value) if value in options else 0
        return st.selectbox(label, options, index=index, key=key, help=f.help)
    if kind == "date":
        return st.date_input(label, value=parse_date(value), key=key, help=f.help, format="MM/DD/YYYY")
    if kind == "int":
        return st.number_input(label, value=int(value or 0), step=1, key=key, help=f.help)
    if kind == "money":
        return st.number_input(label, value=float(value or 0), step=500.0, format="%.2f", key=key, help=f.help)
    if kind == "percent":
        return st.slider(label, 0, 100, int(value or 0), step=5, key=key, help=f.help)
    if kind == "bool":
        return st.checkbox(label, value=bool(value), key=key, help=f.help)
    return st.text_input(label, value or "", key=key, help=f.help)


def form_fields(fields: list[Field], record: dict, prefix: str) -> dict:
    """Lay out inputs in a two-column grid, with long text fields full width."""
    values: dict[str, Any] = {}
    pending: list[Field] = []

    def flush():
        for i in range(0, len(pending), 2):
            cols = st.columns(2)
            for col, f in zip(cols, pending[i:i + 2]):
                with col:
                    values[f.name] = _input(f, record.get(f.name), f"{prefix}_{f.name}")
        pending.clear()

    for f in fields:
        if f.kind == "textarea":
            flush()
            values[f.name] = _input(f, record.get(f.name), f"{prefix}_{f.name}")
        else:
            pending.append(f)
    flush()

    for k, v in values.items():
        if isinstance(v, dt.date):
            values[k] = v.isoformat()
        elif isinstance(v, bool):
            values[k] = int(v)
    return values


def _missing(tool: Tool, values: dict) -> list[str]:
    return [f.label for f in tool.fields if f.required and values.get(f.name) in (None, "")]


def _ref(tool: Tool, record: dict) -> str:
    if tool.number_prefix and record.get("number") is not None:
        return f"{tool.number_prefix}-{int(record['number']):03d}"
    return tool.singular


def _create_dialog(tool: Tool, project_id: int | None) -> None:
    @st.dialog(f"New {tool.singular}", width="large")
    def dialog():
        defaults = {f.name: _default(f) for f in tool.fields}
        with st.form(f"{tool.table}_create", border=False):
            values = form_fields(tool.fields, defaults, f"{tool.table}_new")
            submitted = st.form_submit_button(f"Create {tool.singular}", type="primary", icon=":material/check:")
        if submitted:
            missing = _missing(tool, values)
            if missing:
                st.error("Required: " + ", ".join(missing))
                return
            if tool.project_scoped:
                values["project_id"] = project_id
            if tool.number_prefix:
                values["number"] = db.next_number(tool.table, project_id)
            db.insert(tool.table, values)
            flash(f"{tool.singular} created")
            st.rerun()

    dialog()


def is_overdue(tool: Tool, df: pd.DataFrame) -> pd.Series:
    if df.empty or not tool.due_field or tool.due_field not in df:
        return pd.Series(False, index=df.index)
    due = pd.to_datetime(df[tool.due_field], errors="coerce")
    late = due.dt.date < dt.date.today()
    if tool.status_field:
        late &= ~df[tool.status_field].isin(tool.closed_statuses)
    return late.fillna(False)


def _metrics(tool: Tool, df: pd.DataFrame, overdue: pd.Series) -> None:
    cards: list[tuple[str, Any]] = [("Total", len(df))]
    if tool.status_field and tool.closed_statuses:
        cards.append(("Open", int((~df[tool.status_field].isin(tool.closed_statuses)).sum())))
    if tool.due_field:
        cards.append(("Overdue", int(overdue.sum())))
    for status in tool.metric_statuses:
        cards.append((status, int((df[tool.status_field] == status).sum())))
    if len(cards) == 1:
        return
    for col, (label, value) in zip(st.columns(len(cards)), cards):
        col.metric(label, value, border=True)


def _table(tool: Tool, df: pd.DataFrame, overdue: pd.Series) -> int | None:
    view = pd.DataFrame(index=df.index)
    config: dict[str, Any] = {}
    if tool.number_prefix:
        view["#"] = df["number"].map(lambda n: f"{tool.number_prefix}-{int(n):03d}" if pd.notna(n) else "")
    for f in tool.fields:
        if not f.in_table:
            continue
        col = df[f.name]
        if f.name == tool.status_field:
            view[f.label] = col.map(status_label)
        elif f.kind == "date":
            view[f.label] = pd.to_datetime(col, errors="coerce")
            config[f.label] = st.column_config.DateColumn(format="MMM D, YYYY")
        elif f.kind == "money":
            view[f.label] = col
            config[f.label] = st.column_config.NumberColumn(format="dollar")
        elif f.kind == "percent":
            view[f.label] = col
            config[f.label] = st.column_config.ProgressColumn(min_value=0, max_value=100, format="%d%%")
        elif f.kind == "bool":
            view[f.label] = col.astype(bool)
            config[f.label] = st.column_config.CheckboxColumn()
        elif f.kind == "textarea":
            view[f.label] = col.fillna("").astype(str).str.slice(0, 80)
        else:
            view[f.label] = col
    if tool.due_field and overdue.any():
        view["Overdue"] = overdue.map({True: "⚠️ Overdue", False: ""})

    event = st.dataframe(
        view,
        hide_index=True,
        width="stretch",
        column_config=config,
        on_select="rerun",
        selection_mode="single-row",
        key=f"{tool.table}_grid",
    )
    rows = event.selection.rows if event and event.selection else []
    if rows and rows[0] < len(df):
        return int(df.iloc[rows[0]]["id"])
    return None


def _detail(tool: Tool, record_id: int) -> None:
    record = db.get(tool.table, record_id)
    if not record:
        return
    with st.container(border=True):
        head, badge = st.columns([4, 1], vertical_alignment="center")
        head.subheader(f"{_ref(tool, record)} · {record.get(tool.title_field) or ''}")
        with badge:
            if tool.status_field:
                status_badge(record.get(tool.status_field))
        with st.form(f"{tool.table}_edit_{record_id}", border=False):
            values = form_fields(tool.fields, record, f"{tool.table}_e{record_id}")
            saved = st.form_submit_button("Save changes", type="primary", icon=":material/save:")
        if saved:
            missing = _missing(tool, values)
            if missing:
                st.error("Required: " + ", ".join(missing))
            else:
                db.update(tool.table, record_id, values)
                flash(f"{_ref(tool, record)} updated")
                st.rerun()
        with st.expander("Danger zone", icon=":material/delete:"):
            confirm = st.checkbox(f"Yes, permanently delete this {tool.singular.lower()}",
                                  key=f"{tool.table}_confirm_{record_id}")
            if st.button("Delete", disabled=not confirm, key=f"{tool.table}_del_{record_id}"):
                db.delete(tool.table, record_id)
                flash(f"{_ref(tool, record)} deleted", "🗑️")
                st.rerun()


def render_tool(tool: Tool) -> None:
    show_flash()
    project = require_project() if tool.project_scoped else None
    project_id = project["id"] if project else None

    actions = page_header(tool.title, tool.icon, project)
    if actions.button(f"New {tool.singular}", type="primary", icon=":material/add:",
                      key=f"{tool.table}_new_btn", width="stretch"):
        _create_dialog(tool, project_id)

    df = db.list_records(tool.table, project_id, tool.order_by)
    overdue = is_overdue(tool, df)
    _metrics(tool, df, overdue)

    if tool.extra and not df.empty:
        tool.extra(df)

    # Filters
    c1, c2, c3 = st.columns([2, 2, 1], vertical_alignment="bottom")
    search = c1.text_input("Search", placeholder="Search all text…", key=f"{tool.table}_search",
                           label_visibility="collapsed")
    mask = pd.Series(True, index=df.index)
    if tool.status_field:
        statuses = next((f.options for f in tool.fields if f.name == tool.status_field), None) or []
        chosen = c2.multiselect("Status", statuses, placeholder="All statuses",
                                key=f"{tool.table}_status_filter", label_visibility="collapsed")
        if chosen:
            mask &= df[tool.status_field].isin(chosen)
    if tool.due_field and c3.toggle("Overdue only", key=f"{tool.table}_overdue_only"):
        mask &= overdue
    if search:
        text_cols = [f.name for f in tool.fields if f.kind in ("text", "textarea", "select", "contact")]
        hay = df[text_cols].fillna("").astype(str).agg(" ".join, axis=1)
        if tool.number_prefix:
            hay += " " + df["number"].map(lambda n: f"{tool.number_prefix}-{int(n):03d}" if pd.notna(n) else "")
        mask &= hay.str.contains(search, case=False, regex=False)

    filtered = df[mask]
    if df.empty:
        st.info(f"No {tool.title.lower()} yet. Click **New {tool.singular}** to add one.", icon="📭")
        return

    selected = _table(tool, filtered, overdue[mask])
    left, right = st.columns([3, 1])
    left.caption(f"Showing {len(filtered)} of {len(df)} · select a row to view or edit it")
    export_cols = [c for c in filtered.columns if c not in ("data",)]
    right.download_button("Export CSV", filtered[export_cols].to_csv(index=False).encode(),
                          file_name=f"{tool.table}.csv", mime="text/csv", icon=":material/download:",
                          width="stretch", key=f"{tool.table}_export")
    if selected:
        _detail(tool, selected)
