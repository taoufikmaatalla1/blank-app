# 🏗️ BuildTrack — Construction Project Management

BuildTrack is a construction management app built with Streamlit. It gives
general contractors one place to run their projects: RFIs, submittals, daily
logs, punch lists, budgets, change orders, schedules, documents and a company
directory.

## Features

| Tool | What it does |
| --- | --- |
| **Dashboard** | Project health: open/overdue counts, schedule %, budget over/under, overdue action items, latest daily log, upcoming milestones, and a portfolio table across all projects |
| **Projects** | Create and manage projects (number, client, PM, contract value, dates) and switch between them in the sidebar |
| **RFIs** | Auto-numbered (RFI-001…), with ball-in-court, due dates, priority, cost/schedule impact, question and official answer |
| **Submittals** | Shop drawings, product data and samples, tracked through Draft → Submitted → In Review → Approved / Revise & Resubmit |
| **Daily Log** | Weather, manpower, work performed, deliveries, delays and safety notes, with a manpower trend chart |
| **Punch List** | Items by location, trade and assignee, tracked through to Closed |
| **Budget** | Cost-code budget with a spreadsheet-style editor. Approved change orders roll into the revised budget; projected cost and over/under are calculated per line |
| **Change Orders** | Pending/approved/rejected COs tied to cost codes, with schedule impact in days |
| **Schedule** | Tasks and milestones with a Gantt chart showing progress and today's date |
| **Documents** | Upload drawings, specs, photos and contracts; preview images and download files |
| **Directory** | Companies and contacts; these names fill the assignee drop-downs throughout the app |

Every register has search, status filters, an "overdue only" toggle, CSV export
and select-a-row editing. On first run the app loads three sample projects; use
**Settings → Reset sample data** in the sidebar to start over.

## Run it locally

Prerequisite: install [`uv`](https://docs.astral.sh/uv/).

```
uv sync
uv run streamlit run streamlit_app.py
```

Data is stored in SQLite at `data/buildtrack.db`. Set `BUILDTRACK_DB` to use a
different path.

## Tests

```
cd tests && uv run pytest
```

## Project layout

```
streamlit_app.py        # entry point: sidebar, project picker, navigation
buildtrack/db.py        # SQLite schema, CRUD helpers, sample data
buildtrack/ui.py        # shared "register" page: list, filter, create, edit, delete
buildtrack/tools.py     # field definitions for each tool
buildtrack/finance.py   # budget roll-up math
buildtrack/charts.py    # Altair charts (Gantt, budget, manpower, status)
views/                  # one file per page
tests/                  # smoke and logic tests
```
