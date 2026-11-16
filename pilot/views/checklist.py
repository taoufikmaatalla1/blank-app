"""Launch checklist."""

from __future__ import annotations

import streamlit as st

from .. import db, ui


def render() -> None:
    ctx = ui.load()
    st.title("✅ Launch checklist")
    cdf = ctx.checklist.copy()
    cdf["done"] = cdf["done"].fillna(0).astype(bool)
    done = int(cdf["done"].sum())
    st.progress(done / len(cdf) if len(cdf) else 0.0, text=f"{done} of {len(cdf)} steps done")
    with st.form(f"check_{ui.ver()}"):
        ed = st.data_editor(
            cdf, num_rows="dynamic", hide_index=True, width="stretch",
            column_order=["done", "phase", "step"],
            column_config={"done": st.column_config.CheckboxColumn("Done", width="small"),
                           "phase": st.column_config.TextColumn("Phase", width="medium"),
                           "step": st.column_config.TextColumn("Step", width="large", required=True)})
        if st.form_submit_button("Save", type="primary"):
            ed["done"] = ed["done"].fillna(False).astype(int)
            ed["sort"] = range(1, len(ed) + 1)
            db.write("checklist", ed)
            ui.bump()
            st.rerun()
