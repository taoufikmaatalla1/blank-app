"""Declarative specs for each record-based construction tool."""

from __future__ import annotations

import datetime as dt

from buildtrack.ui import PRIORITIES, TRADES, Field, Tool


def in_days(n: int):
    return lambda: dt.date.today() + dt.timedelta(days=n)


def today():
    return dt.date.today()


RFI_STATUSES = ["Draft", "Open", "Answered", "Closed"]
IMPACT = ["TBD", "Yes", "No"]

RFIS = Tool(
    table="rfis", title="RFIs", singular="RFI", icon="❓", number_prefix="RFI",
    title_field="subject", closed_statuses=("Answered", "Closed"), metric_statuses=("Answered",),
    fields=[
        Field("subject", "Subject", required=True),
        Field("status", "Status", "select", RFI_STATUSES, default="Open"),
        Field("assigned_to", "Ball in court", "contact"),
        Field("priority", "Priority", "select", PRIORITIES, default="Normal"),
        Field("due_date", "Due date", "date", default=in_days(7)),
        Field("spec_section", "Spec section", in_table=False),
        Field("cost_impact", "Cost impact", "select", IMPACT, default="TBD", in_table=False),
        Field("schedule_impact", "Schedule impact", "select", IMPACT, default="TBD", in_table=False),
        Field("created_by", "Created by", "contact", in_table=False),
        Field("question", "Question", "textarea", in_table=False),
        Field("answer", "Official answer", "textarea", in_table=False),
    ],
)

SUBMITTAL_STATUSES = ["Draft", "Submitted", "In Review", "Approved", "Approved as Noted",
                      "Revise & Resubmit", "Rejected"]

SUBMITTALS = Tool(
    table="submittals", title="Submittals", singular="Submittal", icon="📑", number_prefix="SUB",
    closed_statuses=("Approved", "Approved as Noted", "Rejected"), metric_statuses=("In Review",),
    fields=[
        Field("title", "Title", required=True),
        Field("spec_section", "Spec section"),
        Field("type", "Type", "select", ["Shop Drawings", "Product Data", "Samples", "Mock-up",
                                         "Calculations", "O&M Manual", "Warranty"], default="Product Data"),
        Field("status", "Status", "select", SUBMITTAL_STATUSES, default="Draft"),
        Field("submitted_by", "Submitted by", "contact"),
        Field("reviewer", "Reviewer", "contact"),
        Field("revision", "Revision", "int", in_table=False),
        Field("submitted_date", "Submitted", "date", in_table=False),
        Field("due_date", "Review due", "date", default=in_days(14)),
        Field("notes", "Notes", "textarea", in_table=False),
    ],
)

PUNCH_STATUSES = ["Open", "In Progress", "Ready for Review", "Closed"]

PUNCH = Tool(
    table="punch_items", title="Punch List", singular="Punch Item", icon="✅", number_prefix="PL",
    closed_statuses=("Closed",), metric_statuses=("Ready for Review",),
    fields=[
        Field("title", "Title", required=True),
        Field("location", "Location"),
        Field("trade", "Trade", "select", TRADES, default="Finishes"),
        Field("assigned_to", "Assignee", "contact"),
        Field("priority", "Priority", "select", PRIORITIES, default="Normal"),
        Field("status", "Status", "select", PUNCH_STATUSES, default="Open"),
        Field("due_date", "Due date", "date", default=in_days(7)),
        Field("description", "Description", "textarea", in_table=False),
    ],
)

CO_STATUSES = ["Pending", "Approved", "Rejected"]

CHANGE_ORDERS = Tool(
    table="change_orders", title="Change Orders", singular="Change Order", icon="🔁", number_prefix="CO",
    closed_statuses=("Approved", "Rejected"), metric_statuses=("Approved",),
    fields=[
        Field("title", "Title", required=True),
        Field("cost_code", "Cost code", help="Must match a budget line (e.g. 03-000) to roll up."),
        Field("amount", "Amount", "money"),
        Field("days_impact", "Schedule impact (days)", "int"),
        Field("status", "Status", "select", CO_STATUSES, default="Pending"),
        Field("reason", "Reason", "select", ["Owner Request", "Design Change", "Unforeseen Condition",
                                             "Value Engineering", "Allowance", "Other"], default="Owner Request"),
        Field("due_date", "Response due", "date", default=in_days(10)),
        Field("description", "Description", "textarea", in_table=False),
    ],
)

DAILY_LOGS = Tool(
    table="daily_logs", title="Daily Log", singular="Daily Log", icon="📓",
    title_field="log_date", status_field=None, due_field=None, order_by="log_date DESC",
    fields=[
        Field("log_date", "Date", "date", required=True, default=today),
        Field("weather", "Weather", "select", ["Sunny", "Partly Cloudy", "Cloudy", "Light Rain",
                                               "Heavy Rain", "Snow", "Windy"], default="Sunny"),
        Field("temp_high", "High temp (°F)", "int", default=70),
        Field("workers", "Workers on site", "int"),
        Field("hours", "Man-hours", "int"),
        Field("created_by", "Logged by", "contact", in_table=False),
        Field("work_performed", "Work performed", "textarea"),
        Field("deliveries", "Deliveries", "textarea", in_table=False),
        Field("delays", "Delays / issues", "textarea"),
        Field("safety", "Safety notes", "textarea", in_table=False),
    ],
)

SCHEDULE = Tool(
    table="schedule_tasks", title="Schedule", singular="Task", icon="📅",
    title_field="name", status_field=None, due_field=None, order_by="start_date, id",
    fields=[
        Field("name", "Task", required=True),
        Field("phase", "Phase", "select", ["Pre-Construction", "Sitework", "Structure", "Envelope",
                                           "Interiors", "Closeout"], default="Structure"),
        Field("trade", "Trade", "select", TRADES, default="General Contractor"),
        Field("start_date", "Start", "date", required=True, default=today),
        Field("end_date", "Finish", "date", required=True, default=in_days(14)),
        Field("percent_complete", "% complete", "percent"),
        Field("milestone", "Milestone", "bool"),
        Field("notes", "Notes", "textarea", in_table=False),
    ],
)

DIRECTORY = Tool(
    table="contacts", title="Directory", singular="Contact", icon="👥",
    title_field="name", status_field=None, due_field=None, project_scoped=False, order_by="company, name",
    fields=[
        Field("name", "Name", required=True),
        Field("company", "Company"),
        Field("role", "Role"),
        Field("trade", "Trade", "select", TRADES, default="General Contractor"),
        Field("email", "Email"),
        Field("phone", "Phone"),
        Field("notes", "Notes", "textarea", in_table=False),
    ],
)

PROJECT_STATUSES = ["Pre-Construction", "Active", "On Hold", "Complete"]

PROJECTS = Tool(
    table="projects", title="Projects", singular="Project", icon="🏗️",
    title_field="name", due_field=None, project_scoped=False, order_by="number",
    closed_statuses=("Complete",), metric_statuses=("Active",),
    fields=[
        Field("number", "Project #"),
        Field("name", "Project name", required=True),
        Field("client", "Client / Owner"),
        Field("project_manager", "Project manager", "contact"),
        Field("status", "Status", "select", PROJECT_STATUSES, default="Pre-Construction"),
        Field("contract_value", "Contract value", "money"),
        Field("start_date", "Start", "date", default=today),
        Field("end_date", "Completion", "date", default=in_days(365)),
        Field("address", "Address", in_table=False),
        Field("description", "Description", "textarea", in_table=False),
    ],
)
