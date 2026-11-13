"""SQLite persistence layer for BuildTrack.

All data lives in a single SQLite file (``data/buildtrack.db`` by default, or the
path in the ``BUILDTRACK_DB`` environment variable). Tables are created on first
run and populated with realistic sample projects so the app is useful right away.
"""

from __future__ import annotations

import datetime as dt
import os
import random
import sqlite3
from contextlib import closing
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = Path(os.environ.get("BUILDTRACK_DB", ROOT / "data" / "buildtrack.db"))

SCHEMA = """
CREATE TABLE IF NOT EXISTS projects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    number TEXT,
    name TEXT NOT NULL,
    address TEXT,
    client TEXT,
    project_manager TEXT,
    status TEXT DEFAULT 'Active',
    start_date TEXT,
    end_date TEXT,
    contract_value REAL DEFAULT 0,
    description TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS contacts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    company TEXT,
    role TEXT,
    trade TEXT,
    email TEXT,
    phone TEXT,
    notes TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS rfis (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    number INTEGER,
    subject TEXT NOT NULL,
    question TEXT,
    answer TEXT,
    status TEXT DEFAULT 'Open',
    priority TEXT DEFAULT 'Normal',
    assigned_to TEXT,
    created_by TEXT,
    spec_section TEXT,
    due_date TEXT,
    cost_impact TEXT DEFAULT 'TBD',
    schedule_impact TEXT DEFAULT 'TBD',
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS submittals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    number INTEGER,
    title TEXT NOT NULL,
    spec_section TEXT,
    type TEXT,
    status TEXT DEFAULT 'Draft',
    submitted_by TEXT,
    reviewer TEXT,
    revision INTEGER DEFAULT 0,
    submitted_date TEXT,
    due_date TEXT,
    notes TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS daily_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    log_date TEXT NOT NULL,
    weather TEXT,
    temp_high INTEGER,
    workers INTEGER DEFAULT 0,
    hours REAL DEFAULT 0,
    work_performed TEXT,
    deliveries TEXT,
    delays TEXT,
    safety TEXT,
    created_by TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS punch_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    number INTEGER,
    title TEXT NOT NULL,
    location TEXT,
    trade TEXT,
    assigned_to TEXT,
    priority TEXT DEFAULT 'Normal',
    status TEXT DEFAULT 'Open',
    due_date TEXT,
    description TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS budget_lines (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    cost_code TEXT NOT NULL,
    description TEXT,
    original_budget REAL DEFAULT 0,
    committed REAL DEFAULT 0,
    actual REAL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS change_orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    number INTEGER,
    title TEXT NOT NULL,
    cost_code TEXT,
    amount REAL DEFAULT 0,
    days_impact INTEGER DEFAULT 0,
    status TEXT DEFAULT 'Pending',
    reason TEXT,
    description TEXT,
    due_date TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS schedule_tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    phase TEXT,
    trade TEXT,
    start_date TEXT,
    end_date TEXT,
    percent_complete INTEGER DEFAULT 0,
    milestone INTEGER DEFAULT 0,
    notes TEXT
);

CREATE TABLE IF NOT EXISTS documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    category TEXT,
    version TEXT,
    uploaded_by TEXT,
    mime TEXT,
    size INTEGER,
    data BLOB,
    notes TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
"""

TABLES = {
    "projects", "contacts", "rfis", "submittals", "daily_logs", "punch_items",
    "budget_lines", "change_orders", "schedule_tasks", "documents",
}


def _check_table(table: str) -> str:
    if table not in TABLES:
        raise ValueError(f"Unknown table: {table}")
    return table


def connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _columns(conn: sqlite3.Connection, table: str) -> set[str]:
    return {row["name"] for row in conn.execute(f"PRAGMA table_info({table})")}


# --------------------------------------------------------------------------- CRUD


def query_df(sql: str, params: tuple | list = ()) -> pd.DataFrame:
    with closing(connect()) as conn:
        return pd.read_sql_query(sql, conn, params=params)


def fetch_one(sql: str, params: tuple | list = ()) -> dict | None:
    with closing(connect()) as conn:
        row = conn.execute(sql, params).fetchone()
        return dict(row) if row else None


def list_records(table: str, project_id: int | None = None, order_by: str = "id DESC") -> pd.DataFrame:
    _check_table(table)
    sql = f"SELECT * FROM {table}"
    params: list[Any] = []
    if project_id is not None:
        sql += " WHERE project_id = ?"
        params.append(project_id)
    sql += f" ORDER BY {order_by}"
    return query_df(sql, params)


def get(table: str, record_id: int) -> dict | None:
    return fetch_one(f"SELECT * FROM {_check_table(table)} WHERE id = ?", (record_id,))


def insert(table: str, data: dict) -> int:
    _check_table(table)
    with closing(connect()) as conn, conn:
        cols = _columns(conn, table)
        data = {k: v for k, v in data.items() if k in cols and k != "id"}
        keys = ", ".join(data)
        marks = ", ".join("?" for _ in data)
        cur = conn.execute(f"INSERT INTO {table} ({keys}) VALUES ({marks})", list(data.values()))
        return int(cur.lastrowid)


def update(table: str, record_id: int, data: dict) -> None:
    _check_table(table)
    with closing(connect()) as conn, conn:
        cols = _columns(conn, table)
        data = {k: v for k, v in data.items() if k in cols and k != "id"}
        if not data:
            return
        assignments = ", ".join(f"{k} = ?" for k in data)
        conn.execute(f"UPDATE {table} SET {assignments} WHERE id = ?", [*data.values(), record_id])


def delete(table: str, record_id: int) -> None:
    with closing(connect()) as conn, conn:
        conn.execute(f"DELETE FROM {_check_table(table)} WHERE id = ?", (record_id,))


def next_number(table: str, project_id: int) -> int:
    row = fetch_one(
        f"SELECT COALESCE(MAX(number), 0) + 1 AS n FROM {_check_table(table)} WHERE project_id = ?",
        (project_id,),
    )
    return int(row["n"]) if row else 1


def contact_names() -> list[str]:
    df = query_df("SELECT name FROM contacts ORDER BY name")
    return df["name"].tolist()


# --------------------------------------------------------------------------- setup


def init_db(seed: bool = True) -> None:
    with closing(connect()) as conn, conn:
        conn.executescript(SCHEMA)
        empty = conn.execute("SELECT COUNT(*) FROM projects").fetchone()[0] == 0
    if seed and empty:
        seed_sample_data()


def reset_db() -> None:
    """Delete every record and reload the sample data."""
    with closing(connect()) as conn, conn:
        for table in TABLES:
            conn.execute(f"DROP TABLE IF EXISTS {table}")
    init_db(seed=True)


def _d(days: int) -> str:
    return (dt.date.today() + dt.timedelta(days=days)).isoformat()


def seed_sample_data() -> None:
    rng = random.Random(42)

    contacts = [
        ("Sarah Chen", "BuildTrack GC", "Project Manager", "General Contractor", "sarah.chen@example.com", "(555) 201-1001"),
        ("Marcus Johnson", "BuildTrack GC", "Superintendent", "General Contractor", "marcus.j@example.com", "(555) 201-1002"),
        ("Priya Patel", "BuildTrack GC", "Project Engineer", "General Contractor", "priya.p@example.com", "(555) 201-1003"),
        ("David Okafor", "Okafor Architects", "Architect", "Design", "dokafor@example.com", "(555) 310-2200"),
        ("Elena Rossi", "Rossi Structural", "Structural Engineer", "Design", "elena@example.com", "(555) 310-4410"),
        ("Tom Becker", "Becker Electric", "Foreman", "Electrical", "tom@example.com", "(555) 420-7788"),
        ("Luis Hernandez", "Summit Mechanical", "Project Manager", "HVAC / Mechanical", "luis.h@example.com", "(555) 420-3311"),
        ("Grace Kim", "ClearFlow Plumbing", "Foreman", "Plumbing", "grace@example.com", "(555) 420-9090"),
        ("Andre Williams", "Steelworks Inc.", "Estimator", "Structural Steel", "andre@example.com", "(555) 530-1212"),
        ("Hannah Moore", "Riverside Health Group", "Owner's Rep", "Owner", "hmoore@example.com", "(555) 640-5000"),
        ("Jake Thompson", "Precision Drywall", "Foreman", "Drywall / Framing", "jake@example.com", "(555) 530-6464"),
        ("Nadia Ibrahim", "Ibrahim Concrete", "Owner", "Concrete", "nadia@example.com", "(555) 530-8080"),
    ]
    for name, company, role, trade, email, phone in contacts:
        insert("contacts", dict(name=name, company=company, role=role, trade=trade, email=email, phone=phone))

    projects = [
        dict(number="2024-001", name="Riverside Medical Office Building",
             address="1200 River Rd, Springfield", client="Riverside Health Group",
             project_manager="Sarah Chen", status="Active", start_date=_d(-180), end_date=_d(185),
             contract_value=18_500_000,
             description="4-story, 62,000 SF medical office building with structured parking."),
        dict(number="2024-002", name="Maple Street Mixed-Use",
             address="455 Maple St, Springfield", client="Maple Development LLC",
             project_manager="Sarah Chen", status="Active", start_date=_d(-90), end_date=_d(300),
             contract_value=26_750_000,
             description="5-story wood frame over podium: 84 apartments + 12,000 SF retail."),
        dict(number="2025-003", name="Westgate Elementary Renovation",
             address="88 Westgate Ave, Shelbyville", client="Shelbyville School District",
             project_manager="Priya Patel", status="Pre-Construction", start_date=_d(45), end_date=_d(320),
             contract_value=7_200_000,
             description="Interior renovation, MEP upgrades, and new gymnasium addition."),
    ]
    project_ids = [insert("projects", p) for p in projects]

    for idx, pid in enumerate(project_ids):
        scale = [1.0, 1.4, 0.4][idx]
        progress_days = [180, 90, -45][idx]
        _seed_budget(pid, scale, progress_days, rng)
        _seed_schedule(pid, progress_days)
        if progress_days <= 0:
            # Pre-construction project: only a couple of early RFIs/submittals.
            _seed_rfis(pid, rng, limit=2)
            _seed_submittals(pid, rng, limit=3)
            continue
        _seed_rfis(pid, rng)
        _seed_submittals(pid, rng)
        _seed_punch(pid, rng)
        _seed_daily_logs(pid, rng)
        _seed_change_orders(pid, rng, scale)


def _seed_budget(pid: int, scale: float, progress_days: int, rng: random.Random) -> None:
    lines = [
        ("01-000", "General Requirements", 1_150_000),
        ("02-000", "Site Work & Demolition", 820_000),
        ("03-000", "Concrete", 2_400_000),
        ("05-000", "Structural Steel", 2_950_000),
        ("06-000", "Wood, Plastics & Composites", 640_000),
        ("07-000", "Thermal & Moisture Protection", 980_000),
        ("08-000", "Openings (Doors, Windows, Glazing)", 1_300_000),
        ("09-000", "Finishes", 1_750_000),
        ("21-000", "Fire Suppression", 420_000),
        ("22-000", "Plumbing", 1_050_000),
        ("23-000", "HVAC", 2_200_000),
        ("26-000", "Electrical", 1_900_000),
    ]
    elapsed = max(0.0, min(1.0, progress_days / 365))
    for i, (code, desc, amount) in enumerate(lines):
        budget = round(amount * scale, -3)
        commit_ratio = 0 if elapsed == 0 else rng.uniform(0.75, 1.06) if i < 8 else rng.uniform(0.5, 0.98)
        committed = round(budget * commit_ratio, -2)
        actual = round(committed * min(1.0, elapsed * rng.uniform(0.9, 1.6)), -2)
        insert("budget_lines", dict(project_id=pid, cost_code=code, description=desc,
                                    original_budget=budget, committed=committed, actual=actual))


def _seed_schedule(pid: int, progress_days: int) -> None:
    start = dt.date.today() - dt.timedelta(days=progress_days)
    tasks = [
        ("Notice to Proceed", "Pre-Construction", "General Contractor", 0, 0, True),
        ("Permits & Mobilization", "Pre-Construction", "General Contractor", 0, 21, False),
        ("Site Work & Excavation", "Sitework", "Excavation", 14, 35, False),
        ("Foundations", "Structure", "Concrete", 42, 35, False),
        ("Structural Steel Erection", "Structure", "Structural Steel", 70, 56, False),
        ("Elevated Slabs", "Structure", "Concrete", 98, 42, False),
        ("Building Envelope", "Envelope", "Glazing", 133, 63, False),
        ("Roofing", "Envelope", "Roofing", 150, 28, False),
        ("Dried-In", "Envelope", "General Contractor", 196, 0, True),
        ("MEP Rough-In", "Interiors", "HVAC / Mechanical", 160, 70, False),
        ("Framing & Drywall", "Interiors", "Drywall / Framing", 190, 63, False),
        ("Interior Finishes", "Interiors", "Finishes", 240, 70, False),
        ("Commissioning", "Closeout", "HVAC / Mechanical", 300, 35, False),
        ("Substantial Completion", "Closeout", "General Contractor", 340, 0, True),
        ("Punch List & Closeout", "Closeout", "General Contractor", 340, 25, False),
    ]
    today = dt.date.today()
    for name, phase, trade, offset, duration, milestone in tasks:
        s = start + dt.timedelta(days=offset)
        e = s + dt.timedelta(days=duration)
        if e <= today:
            pct = 100
        elif s >= today:
            pct = 0
        else:
            pct = int(round((today - s).days / max(1, duration) * 100 / 5) * 5)
        insert("schedule_tasks", dict(project_id=pid, name=name, phase=phase, trade=trade,
                                      start_date=s.isoformat(), end_date=e.isoformat(),
                                      percent_complete=pct, milestone=int(milestone)))


def _seed_rfis(pid: int, rng: random.Random, limit: int | None = None) -> None:
    rfis = [
        ("Beam size conflict at grid C-4", "Structural drawing S-201 shows W18x35 at grid C-4 but architectural section A-501 indicates W16x31. Please confirm the correct member size.", "Use W18x35 per S-201. Architectural section to be revised in next ASI.", "Closed", "High", "Elena Rossi", "05 12 00", "No", "No"),
        ("Curtain wall anchor embed spacing", "Embed plate spacing on S-501 does not match the curtain wall shop drawings (48\" vs 60\" o.c.). Which governs?", "", "Open", "High", "David Okafor", "08 44 13", "TBD", "Yes"),
        ("Ceiling height in Exam Rooms 201-214", "Ductwork in corridor conflicts with 9'-0\" ceiling. Can ceiling be lowered to 8'-6\" in exam rooms?", "", "Open", "Normal", "David Okafor", "09 51 13", "No", "TBD"),
        ("Fire damper access panels", "Several fire dampers above hard-lid ceilings lack access panels on drawings. Please provide locations.", "Provide 24x24 access panels at each FD location. See attached markup.", "Answered", "Normal", "Luis Hernandez", "23 33 00", "Yes", "No"),
        ("Electrical room door swing", "Door 112 swings into the required electrical working clearance. Please advise.", "", "Open", "Low", "Tom Becker", "08 11 13", "No", "No"),
        ("Plumbing riser relocation at Level 3", "Existing column conflicts with the 4\" storm riser location. Request approval to offset riser 18\" north.", "Offset approved. Coordinate with framing.", "Closed", "Normal", "Grace Kim", "22 14 00", "No", "No"),
        ("Exterior paint color substitution", "Specified color is discontinued. Requesting approval of equivalent color from alternate manufacturer.", "", "Draft", "Low", "David Okafor", "09 91 13", "TBD", "No"),
    ]
    for i, (subject, q, a, status, priority, assignee, spec, cost, sched) in enumerate(rfis[:limit]):
        created = rng.randint(5, 60)
        due = -created + rng.choice([7, 10, 14])
        insert("rfis", dict(project_id=pid, number=i + 1, subject=subject, question=q, answer=a,
                            status=status, priority=priority, assigned_to=assignee,
                            created_by="Priya Patel", spec_section=spec, due_date=_d(due),
                            cost_impact=cost, schedule_impact=sched,
                            created_at=_d(-created) + " 09:00:00"))


def _seed_submittals(pid: int, rng: random.Random, limit: int | None = None) -> None:
    subs = [
        ("Concrete Mix Designs", "03 30 00", "Product Data", "Approved", "Nadia Ibrahim"),
        ("Structural Steel Shop Drawings", "05 12 00", "Shop Drawings", "Approved as Noted", "Andre Williams"),
        ("Curtain Wall System", "08 44 13", "Shop Drawings", "In Review", "David Okafor"),
        ("Rooftop Units (RTU-1 to RTU-4)", "23 74 13", "Product Data", "Revise & Resubmit", "Luis Hernandez"),
        ("Lighting Fixtures", "26 51 00", "Product Data", "Submitted", "Tom Becker"),
        ("Plumbing Fixtures", "22 40 00", "Product Data", "In Review", "Grace Kim"),
        ("Gypsum Board Assemblies", "09 21 16", "Product Data", "Draft", "Jake Thompson"),
        ("Roofing Membrane Samples", "07 54 23", "Samples", "Approved", "David Okafor"),
    ]
    for i, (title, spec, typ, status, by) in enumerate(subs[:limit]):
        submitted = -rng.randint(3, 50)
        insert("submittals", dict(project_id=pid, number=i + 1, title=title, spec_section=spec, type=typ,
                                  status=status, submitted_by=by, reviewer="David Okafor",
                                  revision=1 if status == "Revise & Resubmit" else 0,
                                  submitted_date=None if status == "Draft" else _d(submitted),
                                  due_date=_d(submitted + 14)))


def _seed_punch(pid: int, rng: random.Random) -> None:
    items = [
        ("Touch-up paint at corridor walls", "Level 1 - Corridor 100", "Finishes", "Jake Thompson"),
        ("Missing cover plate at receptacle", "Level 2 - Room 204", "Electrical", "Tom Becker"),
        ("Ceiling tile damaged", "Level 2 - Exam 211", "Finishes", "Jake Thompson"),
        ("Door closer needs adjustment", "Level 1 - Door 105", "Openings", "Marcus Johnson"),
        ("Leak at lavatory P-trap", "Level 3 - Restroom 301", "Plumbing", "Grace Kim"),
        ("Diffuser not aligned with grid", "Level 3 - Office 315", "HVAC / Mechanical", "Luis Hernandez"),
        ("Scratched storefront frame", "Level 1 - Main Entry", "Glazing", "Marcus Johnson"),
        ("Caulk joint incomplete at window", "Level 4 - Room 402", "Finishes", "Jake Thompson"),
        ("Exit sign not illuminated", "Stair 2 - Level 3", "Electrical", "Tom Becker"),
        ("Floor transition strip missing", "Level 2 - Corridor 200", "Finishes", "Jake Thompson"),
    ]
    statuses = ["Open", "Open", "In Progress", "Ready for Review", "Closed"]
    for i, (title, loc, trade, assignee) in enumerate(items):
        insert("punch_items", dict(project_id=pid, number=i + 1, title=title, location=loc, trade=trade,
                                   assigned_to=assignee, priority=rng.choice(["Low", "Normal", "Normal", "High"]),
                                   status=rng.choice(statuses), due_date=_d(rng.randint(-6, 14))))


def _seed_daily_logs(pid: int, rng: random.Random) -> None:
    weather = ["Sunny", "Partly Cloudy", "Cloudy", "Light Rain", "Sunny", "Windy"]
    work = [
        "Steel erection continued on east bay. Deck installation at Level 3.",
        "Poured Level 2 slab on deck (85 CY). Curing compound applied.",
        "MEP rough-in on Level 1. Electrical conduit overhead in corridor.",
        "Curtain wall anchors installed on south elevation. Framing layout Level 2.",
        "Roof insulation and membrane installation on north half.",
        "Fireproofing applied to Level 3 steel. Plumbing risers tested.",
        "Drywall hanging on Level 1. Inspection passed for above-ceiling at Level 2.",
    ]
    day = dt.date.today()
    logs = 0
    while logs < 14:
        day -= dt.timedelta(days=1)
        if day.weekday() >= 5:
            continue
        w = rng.choice(weather)
        workers = rng.randint(28, 64)
        insert("daily_logs", dict(project_id=pid, log_date=day.isoformat(), weather=w,
                                  temp_high=rng.randint(48, 82), workers=workers,
                                  hours=workers * 8, work_performed=rng.choice(work),
                                  deliveries=rng.choice(["", "Rebar delivery (12 tons)", "Drywall (2 trucks)", "Steel joists"]),
                                  delays="Rain delay 2 hrs - exterior work stopped" if w == "Light Rain" else "",
                                  safety=rng.choice(["Toolbox talk: fall protection", "No incidents", "Toolbox talk: ladder safety", "No incidents"]),
                                  created_by="Marcus Johnson"))
        logs += 1


def _seed_change_orders(pid: int, rng: random.Random, scale: float) -> None:
    cos = [
        ("Owner-requested lobby finish upgrade", "09-000", 48_500, "Approved", "Owner Request", 0),
        ("Unforeseen rock excavation", "02-000", 72_300, "Approved", "Unforeseen Condition", 6),
        ("Add access panels per RFI #4", "23-000", 8_900, "Pending", "Design Change", 0),
        ("Curtain wall anchor redesign", "08-000", 31_200, "Pending", "Design Change", 4),
        ("Value engineering: lighting fixtures", "26-000", -22_000, "Approved", "Value Engineering", 0),
        ("Additional data drops in exam rooms", "26-000", 14_750, "Rejected", "Owner Request", 0),
    ]
    for i, (title, code, amount, status, reason, days) in enumerate(cos):
        insert("change_orders", dict(project_id=pid, number=i + 1, title=title, cost_code=code,
                                     amount=round(amount * scale, -1), status=status, reason=reason,
                                     days_impact=days, due_date=_d(rng.randint(-5, 20))))
