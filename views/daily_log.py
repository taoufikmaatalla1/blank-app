import streamlit as st

from buildtrack import charts
from buildtrack.tools import DAILY_LOGS
from buildtrack.ui import render_tool


def manpower_section(df):
    with st.container(border=True):
        st.markdown("**Manpower trend**")
        st.altair_chart(charts.manpower(df), width="stretch")


DAILY_LOGS.extra = manpower_section
render_tool(DAILY_LOGS)
