"""BuildTrack — construction project management.

Run with:  uv run streamlit run streamlit_app.py
"""

import streamlit as st

from buildtrack import db

st.set_page_config(page_title="BuildTrack", page_icon="🏗️", layout="wide")
db.init_db()

pages = {
    "Overview": [
        st.Page("views/dashboard.py", title="Dashboard", icon=":material/dashboard:", default=True),
        st.Page("views/projects.py", title="Projects", icon=":material/apartment:"),
    ],
    "Project Management": [
        st.Page("views/rfis.py", title="RFIs", icon=":material/help:"),
        st.Page("views/submittals.py", title="Submittals", icon=":material/assignment_turned_in:"),
        st.Page("views/daily_log.py", title="Daily Log", icon=":material/edit_note:"),
        st.Page("views/punch_list.py", title="Punch List", icon=":material/checklist:"),
    ],
    "Financials": [
        st.Page("views/budget.py", title="Budget", icon=":material/payments:"),
        st.Page("views/change_orders.py", title="Change Orders", icon=":material/published_with_changes:"),
    ],
    "Planning & Docs": [
        st.Page("views/schedule.py", title="Schedule", icon=":material/calendar_month:"),
        st.Page("views/documents.py", title="Documents", icon=":material/folder_open:"),
        st.Page("views/directory.py", title="Directory", icon=":material/groups:"),
    ],
}

nav = st.navigation(pages, position="hidden")

with st.sidebar:
    st.markdown("## 🏗️ BuildTrack")
    projects = db.query_df("SELECT id, number, name FROM projects ORDER BY number, name")
    if projects.empty:
        st.session_state["project_id"] = None
        st.caption("No projects yet.")
    else:
        ids = [int(i) for i in projects["id"]]
        labels = {int(r.id): f"{r.number} · {r.name}" if r.number else r.name for r in projects.itertuples()}
        if st.session_state.get("project_id") not in ids:
            st.session_state["project_id"] = ids[0]
        st.selectbox("Current project", ids, format_func=labels.get, key="project_id")

    for section, section_pages in pages.items():
        st.caption(section.upper())
        for page in section_pages:
            st.page_link(page)

    st.divider()
    with st.expander("Settings", icon=":material/settings:"):
        st.caption("Wipe all data and reload the sample projects.")
        if st.button("Reset sample data", icon=":material/restart_alt:"):
            db.reset_db()
            st.session_state.pop("project_id", None)
            st.rerun()

nav.run()
