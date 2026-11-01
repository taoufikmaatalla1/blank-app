import pandas as pd
import streamlit as st

from buildtrack import db
from buildtrack.ui import flash, page_header, require_project, show_flash

CATEGORIES = ["Drawings", "Specifications", "Photos", "Contracts", "Permits", "Reports", "Submittals",
              "Meeting Minutes", "Other"]

show_flash()
project = require_project()
pid = project["id"]
actions = page_header("Documents", "📁", project)


@st.dialog("Upload documents", width="large")
def upload_dialog():
    with st.form("doc_upload", border=False):
        files = st.file_uploader("Files", accept_multiple_files=True)
        c1, c2 = st.columns(2)
        category = c1.selectbox("Category", CATEGORIES)
        version = c2.text_input("Version / revision", "Rev 0")
        uploaded_by = c1.selectbox("Uploaded by", [""] + db.contact_names())
        notes = st.text_area("Notes", height=80)
        submitted = st.form_submit_button("Upload", type="primary", icon=":material/upload:")
    if submitted:
        if not files:
            st.error("Choose at least one file.")
            return
        for f in files:
            data = f.getvalue()
            db.insert("documents", dict(project_id=pid, name=f.name, category=category, version=version,
                                        uploaded_by=uploaded_by, mime=f.type, size=len(data), data=data,
                                        notes=notes))
        flash(f"Uploaded {len(files)} file(s)")
        st.rerun()


if actions.button("Upload", type="primary", icon=":material/upload:", width="stretch"):
    upload_dialog()

docs = db.query_df(
    "SELECT id, name, category, version, uploaded_by, mime, size, notes, created_at "
    "FROM documents WHERE project_id = ? ORDER BY created_at DESC", (pid,))

if docs.empty:
    st.info("No documents yet. Upload drawings, specs, photos, or contracts to keep them with the project.",
            icon="📭")
    st.stop()

c1, c2, c3 = st.columns(3)
c1.metric("Files", len(docs), border=True)
c2.metric("Categories", docs["category"].nunique(), border=True)
c3.metric("Storage used", f"{docs['size'].sum() / 1_048_576:.1f} MB", border=True)

f1, f2 = st.columns([2, 2])
search = f1.text_input("Search", placeholder="Search file names and notes…", label_visibility="collapsed")
cats = f2.multiselect("Category", CATEGORIES, placeholder="All categories", label_visibility="collapsed")
mask = pd.Series(True, index=docs.index)
if search:
    mask &= (docs["name"].fillna("") + " " + docs["notes"].fillna("")).str.contains(search, case=False, regex=False)
if cats:
    mask &= docs["category"].isin(cats)
view = docs[mask]

table = pd.DataFrame({
    "File": view["name"],
    "Category": view["category"],
    "Version": view["version"],
    "Uploaded by": view["uploaded_by"],
    "Size (KB)": (view["size"].fillna(0) / 1024).round(1),
    "Uploaded": pd.to_datetime(view["created_at"], errors="coerce"),
})
event = st.dataframe(table, hide_index=True, width="stretch", on_select="rerun", selection_mode="single-row",
                     column_config={"Uploaded": st.column_config.DatetimeColumn(format="MMM D, YYYY h:mm a")},
                     key="docs_grid")
st.caption("Select a file to preview, download, or delete it.")

rows = event.selection.rows if event and event.selection else []
if rows and rows[0] < len(view):
    doc_id = int(view.iloc[rows[0]]["id"])
    doc = db.get("documents", doc_id)
    with st.container(border=True):
        st.subheader(doc["name"])
        st.caption(f"{doc['category']} · {doc['version']} · uploaded by {doc['uploaded_by'] or '—'}")
        if doc.get("notes"):
            st.write(doc["notes"])
        mime = doc.get("mime") or ""
        if mime.startswith("image/"):
            st.image(doc["data"], width=600)
        elif mime.startswith("text/") or mime in ("application/json", "text/csv"):
            st.code(bytes(doc["data"]).decode(errors="replace")[:5000])
        b1, b2 = st.columns([1, 3])
        b1.download_button("Download", doc["data"], file_name=doc["name"], mime=mime or None,
                           icon=":material/download:", width="stretch")
        with b2.popover("Delete", icon=":material/delete:"):
            st.write(f"Permanently delete **{doc['name']}**?")
            if st.button("Delete file", type="primary", key=f"del_doc_{doc_id}"):
                db.delete("documents", doc_id)
                flash("Document deleted", "🗑️")
                st.rerun()
