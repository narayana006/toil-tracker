from datetime import datetime, timezone

import pytest

from toil_tracker.loader import InputError, load_csv, parse_time

UTC = timezone.utc


def test_minimal_csv_and_defaults():
    items = load_csv("title,created_at\nB,2026-09-02T10:00:00Z\n\nA,2026-09-01 09:30\n")
    assert [i.title for i in items] == ["A", "B"]  # sorted by time, blank line skipped
    assert items[0].created_at == datetime(2026, 9, 1, 9, 30, tzinfo=UTC)
    assert items[0].kind == "ticket" and items[0].minutes is None and items[0].assignee == ""


def test_column_aliases_types_and_effort_columns():
    text = (
        "﻿Key,Summary,Created,Issue Type,Time Spent Hours,Owner\n"
        "OPS-1,Disk full,2026-09-01,Incident,0.5,asha\n"
        "OPS-2,Add user,01/09/2026 14:00,Task,,ben\n"
    )
    first, second = load_csv(text)
    assert (first.id, first.kind, first.minutes, first.assignee) == ("OPS-1", "page", 30.0, "asha")
    assert (second.kind, second.minutes) == ("ticket", None)
    assert second.created_at == datetime(2026, 9, 1, 14, 0, tzinfo=UTC)


def test_minutes_take_precedence_over_hours():
    item = load_csv("title,created_at,minutes_spent,hours_spent\nA,2026-09-01,20,5\n")[0]
    assert item.minutes == 20


def test_parse_time_with_offset():
    assert parse_time("2026-09-01T12:00:00+02:00") == datetime(2026, 9, 1, 10, tzinfo=UTC)


@pytest.mark.parametrize("text, message", [
    ("name_x,created_at\nA,2026-09-01\n", r"missing required column\(s\): title"),
    ("foo,bar\n1,2\n", r"missing required column\(s\): title, created_at"),
    ("title,created_at\n,2026-09-01\n", "line 2: empty title"),
    ("title,created_at\nA,\n", "line 2: empty created_at"),
    ("title,created_at\nA,2026-09-01\nB,soon\n", "line 3: cannot parse date 'soon'"),
    ("title,created_at,minutes_spent\nA,2026-09-01,lots\n", "line 2: minutes_spent is not a number"),
    ("title,created_at,minutes_spent\nA,2026-09-01,-5\n", "line 2: minutes_spent is negative"),
])
def test_errors(text, message):
    with pytest.raises(InputError, match=message):
        load_csv(text)


def test_empty_file_has_no_columns():
    with pytest.raises(InputError, match="missing required column"):
        load_csv("")
