"""Read tickets and pages from a CSV export."""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass
from datetime import datetime, timezone

# Canonical field -> accepted column names (case-insensitive, spaces or underscores).
COLUMN_ALIASES: dict[str, tuple[str, ...]] = {
    "title": ("title", "summary", "subject", "description", "name"),
    "created_at": ("created_at", "created", "opened_at", "triggered_at", "date"),
    "minutes_spent": ("minutes_spent", "time_spent_minutes", "minutes", "effort_minutes"),
    "hours_spent": ("hours_spent", "time_spent_hours", "hours", "effort_hours"),
    "type": ("type", "kind", "issue_type", "source"),
    "assignee": ("assignee", "owner", "assigned_to", "responder"),
    "id": ("id", "key", "ticket", "number"),
}
PAGE_TYPES = ("page", "incident", "alert", "pagerduty", "opsgenie")


class InputError(ValueError):
    """The CSV is missing required columns or contains an unreadable value."""


@dataclass(frozen=True)
class WorkItem:
    title: str
    created_at: datetime
    kind: str = "ticket"            # "ticket" or "page"
    minutes: float | None = None    # recorded effort; None when the export has none
    assignee: str = ""
    id: str = ""


def parse_time(value: str) -> datetime:
    text = value.strip()
    if text[-1:] in ("z", "Z"):
        text = text[:-1] + "+00:00"
    for candidate in (text.replace(" ", "T", 1), text):
        try:
            parsed = datetime.fromisoformat(candidate)
            break
        except ValueError:
            continue
    else:
        for fmt in ("%d/%m/%Y %H:%M", "%d/%m/%Y", "%Y/%m/%d %H:%M", "%Y/%m/%d"):
            try:
                parsed = datetime.strptime(text, fmt)
                break
            except ValueError:
                continue
        else:
            raise InputError(f"cannot parse date {value!r}")
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def _number(value: str, column: str) -> float | None:
    if not value.strip():
        return None
    try:
        number = float(value)
    except ValueError as error:
        raise InputError(f"{column} is not a number: {value!r}") from error
    if number < 0:
        raise InputError(f"{column} is negative: {value!r}")
    return number


def load_csv(text: str) -> list[WorkItem]:
    reader = csv.DictReader(io.StringIO(text.lstrip("﻿")))
    header = {(name or "").strip().lower().replace(" ", "_"): name for name in reader.fieldnames or []}
    columns = {field: next((header[a] for a in aliases if a in header), None)
               for field, aliases in COLUMN_ALIASES.items()}
    missing = [field for field in ("title", "created_at") if columns[field] is None]
    if missing:
        raise InputError("missing required column(s): " + ", ".join(missing))

    def cell(row: dict, field: str) -> str:
        column = columns[field]
        return (row.get(column) or "").strip() if column else ""

    items = []
    for row in reader:
        if not any((v or "").strip() for v in row.values() if isinstance(v, str)):
            continue
        try:
            title = cell(row, "title")
            if not title:
                raise InputError("empty title")
            if not cell(row, "created_at"):
                raise InputError("empty created_at")
            minutes = _number(cell(row, "minutes_spent"), "minutes_spent")
            if minutes is None:
                hours = _number(cell(row, "hours_spent"), "hours_spent")
                minutes = None if hours is None else hours * 60
            kind = "page" if cell(row, "type").lower() in PAGE_TYPES else "ticket"
            items.append(WorkItem(title, parse_time(cell(row, "created_at")), kind, minutes,
                                  cell(row, "assignee"), cell(row, "id")))
        except InputError as error:
            raise InputError(f"line {reader.line_num}: {error}") from error
    return sorted(items, key=lambda item: item.created_at)
