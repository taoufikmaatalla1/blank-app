"""Smoke tests: every page renders without exceptions against a fresh sample database."""

import os
import tempfile

import pytest
from streamlit.testing.v1 import AppTest

os.environ["BUILDTRACK_DB"] = os.path.join(tempfile.mkdtemp(), "test.db")

PAGES = ["dashboard", "projects", "rfis", "submittals", "daily_log", "punch_list", "budget",
         "change_orders", "schedule", "documents", "directory"]


@pytest.mark.parametrize("page", PAGES)
def test_page_renders(page):
    at = AppTest.from_file("../streamlit_app.py", default_timeout=30)
    at.run()
    at.switch_page(f"views/{page}.py").run()
    assert not at.exception, at.exception


def test_budget_rollup_includes_approved_change_orders():
    from buildtrack import db
    from buildtrack.finance import budget_summary

    db.init_db()
    pid = int(db.query_df("SELECT id FROM projects ORDER BY id LIMIT 1")["id"][0])
    summary = budget_summary(pid)
    cos = db.list_records("change_orders", pid)
    approved = cos.loc[cos["status"] == "Approved", "amount"].sum()
    assert summary["Approved COs"].sum() == pytest.approx(approved)
    assert (summary["Revised Budget"] == summary["Original Budget"] + summary["Approved COs"]).all()


def test_crud_and_numbering():
    from buildtrack import db

    db.init_db()
    pid = int(db.query_df("SELECT id FROM projects ORDER BY id LIMIT 1")["id"][0])
    n = db.next_number("rfis", pid)
    rid = db.insert("rfis", {"project_id": pid, "number": n, "subject": "Test RFI", "status": "Open"})
    assert db.next_number("rfis", pid) == n + 1
    db.update("rfis", rid, {"status": "Closed"})
    assert db.get("rfis", rid)["status"] == "Closed"
    db.delete("rfis", rid)
    assert db.get("rfis", rid) is None
