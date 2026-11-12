"""SQLite storage. One file (data/pilot.db by default, or $PILOT_DB)."""

from __future__ import annotations

import json
import os
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import pandas as pd

from . import seed

DB_PATH = Path(os.environ.get("PILOT_DB", Path(__file__).resolve().parent.parent / "data" / "pilot.db"))

# table -> {column: sqlite type}; every table also has `id INTEGER PRIMARY KEY`.
SCHEMA: dict[str, dict[str, str]] = {
    "products": {
        "name": "TEXT", "pack": "TEXT", "sale_price": "REAL", "unit_cost_usd": "REAL",
        "freight_per_unit": "REAL", "duty_pct": "REAL", "referral_pct": "REAL", "fba_fee": "REAL",
        "ads_pct": "REAL", "other_per_unit": "REAL", "first_order_qty": "INTEGER",
        "first_order_fixed": "REAL", "asin": "TEXT", "sku": "TEXT", "notes": "TEXT",
    },
    "suppliers": {
        "product_id": "INTEGER", "name": "TEXT", "url": "TEXT", "contact": "TEXT", "status": "TEXT",
        "unit_price_usd": "REAL", "moq": "INTEGER", "lead_time_days": "INTEGER",
        "trade_assurance": "INTEGER", "years_on_alibaba": "INTEGER", "rating": "REAL", "notes": "TEXT",
    },
    "competitors": {
        "product_id": "INTEGER", "asin": "TEXT", "title": "TEXT", "price": "REAL", "rating": "REAL",
        "reviews": "INTEGER", "bsr": "INTEGER", "monthly_sales_est": "INTEGER", "notes": "TEXT",
    },
    "orders": {
        "product_id": "INTEGER", "supplier_id": "INTEGER", "order_date": "TEXT", "qty": "INTEGER",
        "unit_price_usd": "REAL", "shipping_usd": "REAL", "status": "TEXT", "paid_gbp": "REAL",
        "tracking": "TEXT", "eta": "TEXT", "notes": "TEXT",
    },
    "listings": {
        "product_id": "INTEGER", "title": "TEXT", "bullets": "TEXT", "description": "TEXT",
        "search_terms": "TEXT", "status": "TEXT",
    },
    "ads": {
        "product_id": "INTEGER", "campaign": "TEXT", "daily_budget": "REAL", "cpc": "REAL",
        "conversion_rate": "REAL", "keywords": "TEXT", "status": "TEXT",
    },
    "checklist": {"phase": "TEXT", "step": "TEXT", "done": "INTEGER", "sort": "INTEGER"},
}

SUPPLIER_STATUSES = ["To contact", "Message ready", "Sent", "Quote received",
                     "Sample ordered", "Selected", "Rejected"]
ORDER_STATUSES = ["Draft", "Awaiting payment", "Paid", "In production", "Shipped",
                  "At Amazon FC", "Cancelled"]


@contextmanager
def connect() -> Iterator[sqlite3.Connection]:
    """Open the database, commit on success, roll back on error, always close."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    try:
        with con:
            yield con
    finally:
        con.close()


def init(force_seed: bool = False) -> None:
    with connect() as con:
        con.execute("CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)")
        for table, cols in SCHEMA.items():
            col_sql = ", ".join(f"{c} {t}" for c, t in cols.items())
            con.execute(f"CREATE TABLE IF NOT EXISTS {table} (id INTEGER PRIMARY KEY, {col_sql})")
        empty = con.execute("SELECT COUNT(*) FROM products").fetchone()[0] == 0
    if force_seed or empty:
        load_snapshot(seed.snapshot())


def get_settings() -> dict:
    with connect() as con:
        rows = con.execute("SELECT key, value FROM settings").fetchall()
    out = dict(seed.DEFAULT_SETTINGS)
    out.update({r["key"]: json.loads(r["value"]) for r in rows})
    return out


def save_settings(values: dict) -> None:
    with connect() as con:
        con.executemany(
            "INSERT INTO settings(key, value) VALUES(?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            [(k, json.dumps(v)) for k, v in values.items()],
        )


def read(table: str) -> pd.DataFrame:
    cols = ["id", *SCHEMA[table]]
    with connect() as con:
        df = pd.read_sql_query(f"SELECT {', '.join(cols)} FROM {table} ORDER BY id", con)
    return df


def records(table: str) -> list[dict]:
    return read(table).to_dict("records")


def _clean(value):
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    if hasattr(value, "item"):  # numpy scalar -> python
        return value.item()
    return value


def write(table: str, df: pd.DataFrame) -> None:
    """Replace the table's contents with `df` (keeps ids that are present)."""
    cols = ["id", *SCHEMA[table]]
    df = df.reindex(columns=cols)
    rows = [tuple(_clean(v) for v in row) for row in df.itertuples(index=False, name=None)]
    with connect() as con:
        con.execute(f"DELETE FROM {table}")
        con.executemany(
            f"INSERT INTO {table} ({', '.join(cols)}) VALUES ({', '.join('?' * len(cols))})", rows
        )


def insert(table: str, values: dict) -> int:
    cols = [c for c in values if c in SCHEMA[table]]
    with connect() as con:
        cur = con.execute(
            f"INSERT INTO {table} ({', '.join(cols)}) VALUES ({', '.join('?' * len(cols))})",
            [_clean(values[c]) for c in cols],
        )
        return int(cur.lastrowid)


def update(table: str, row_id: int, values: dict) -> None:
    cols = [c for c in values if c in SCHEMA[table]]
    if not cols:
        return
    with connect() as con:
        con.execute(
            f"UPDATE {table} SET {', '.join(f'{c} = ?' for c in cols)} WHERE id = ?",
            [*(_clean(values[c]) for c in cols), row_id],
        )


def delete(table: str, row_id: int) -> None:
    with connect() as con:
        con.execute(f"DELETE FROM {table} WHERE id = ?", (row_id,))
        if table == "products":
            for child in ("suppliers", "competitors", "orders", "listings", "ads"):
                con.execute(f"DELETE FROM {child} WHERE product_id = ?", (row_id,))


def snapshot() -> dict:
    """Everything as plain JSON (for backup / download)."""
    return {"settings": get_settings(), **{t: records(t) for t in SCHEMA}}


def load_snapshot(data: dict) -> None:
    with connect() as con:
        con.execute("DELETE FROM settings")
    save_settings({**seed.DEFAULT_SETTINGS, **data.get("settings", {})})
    for table in SCHEMA:
        write(table, pd.DataFrame(data.get(table, []), columns=["id", *SCHEMA[table]]))


# ---------------------------------------------------------------- integrations
# Tokens and webhook events live in their own tables, which are never included
# in the downloadable backup.

def _init_private(con: sqlite3.Connection) -> None:
    con.execute("CREATE TABLE IF NOT EXISTS secrets (key TEXT PRIMARY KEY, value TEXT)")
    con.execute("CREATE TABLE IF NOT EXISTS events (id INTEGER PRIMARY KEY, source TEXT, "
                "kind TEXT, dedup_key TEXT UNIQUE, received_at TEXT, payload TEXT, "
                "processed INTEGER DEFAULT 0)")


def get_secret(key: str, default=None):
    with connect() as con:
        _init_private(con)
        row = con.execute("SELECT value FROM secrets WHERE key = ?", (key,)).fetchone()
    return json.loads(row["value"]) if row else default


def set_secret(key: str, value) -> None:
    with connect() as con:
        _init_private(con)
        con.execute("INSERT INTO secrets(key, value) VALUES(?, ?) "
                    "ON CONFLICT(key) DO UPDATE SET value = excluded.value", (key, json.dumps(value)))


def add_event(source: str, kind: str, dedup_key: str, payload: str) -> bool:
    """Store a webhook event. Returns False if it was already received (duplicate)."""
    from datetime import datetime, timezone
    with connect() as con:
        _init_private(con)
        cur = con.execute(
            "INSERT OR IGNORE INTO events(source, kind, dedup_key, received_at, payload) "
            "VALUES(?, ?, ?, ?, ?)",
            (source, kind, dedup_key, datetime.now(timezone.utc).isoformat(timespec="seconds"), payload))
        return cur.rowcount == 1


def events(limit: int = 50) -> pd.DataFrame:
    with connect() as con:
        _init_private(con)
        return pd.read_sql_query(
            "SELECT id, source, kind, received_at, payload FROM events ORDER BY id DESC LIMIT ?",
            con, params=(limit,))
