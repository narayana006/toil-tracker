from datetime import datetime, timedelta, timezone

import pytest

from toil_tracker.analysis import DAYS_PER_MONTH, Settings, analyze, cluster, parse_since
from toil_tracker.loader import WorkItem

T0 = datetime(2026, 8, 1, tzinfo=timezone.utc)


def item(title, day, kind="ticket", minutes=None, assignee=""):
    return WorkItem(title, T0 + timedelta(days=day), kind, minutes, assignee)


def test_empty_input():
    report = analyze([])
    assert report.total_items == 0 and report.groups == [] and report.start is None


def test_groups_by_normalised_title_and_separates_one_offs():
    items = [item(f"Disk full on db-{n:02d}", n, "page", 20, f"p{n % 2}") for n in range(6)]
    items += [item("Design review for failover", 3, minutes=120), item("Disk cleanup", 60)]
    report = analyze(items)
    assert len(report.groups) == 1
    group = report.groups[0]
    assert (group.count, group.pages, group.tickets, group.people) == (6, 6, 0, 2)
    assert group.template == "disk full on <host>"
    assert group.example == "Disk full on db-00"
    assert group.hours == 2.0
    assert (group.first_seen, group.last_seen) == ("2026-08-01", "2026-08-06")
    assert (report.one_off_items, report.one_off_hours) == (2, 2.5)
    assert (report.repetitive_items, report.repetitive_hours, report.total_hours) == (6, 2.0, 4.5)


def test_hours_per_month_uses_the_period_length():
    # 12 items of 60 minutes over exactly two average months -> 6 hours per month
    span = 2 * DAYS_PER_MONTH
    items = [item("Rotate key for svc-1", span * n / 11, minutes=60) for n in range(12)]
    report = analyze(items)
    assert report.months == 2.0
    assert report.groups[0].hours_per_month == 6.0
    assert report.groups[0].items_per_month == 6.0


def test_default_effort_and_estimated_share():
    items = [item("Reset password for user 1", 0), item("Reset password for user 2", 10, minutes=90),
             item("Reset password for user 3", 20, "page")]
    group = analyze(items, Settings(ticket_minutes=30, page_minutes=60)).groups[0]
    assert group.hours == 3.0                  # 30 assumed + 90 recorded + 60 assumed
    assert group.estimated_share == 0.5


def test_ranked_by_hours_per_month_not_count():
    frequent = [item(f"Unlock account {n}", n, minutes=5) for n in range(10)]
    costly = [item(f"Rebuild index on shard-{n}", n * 3, minutes=120) for n in range(3)]
    report = analyze(frequent + costly)
    assert [g.count for g in report.groups] == [3, 10]
    assert report.groups[0].hours_per_month > report.groups[1].hours_per_month


def test_min_count_setting():
    items = [item("Renew license for tool-1", 0), item("Renew license for tool-2", 30)]
    assert analyze(items).groups == []
    assert analyze(items, Settings(min_count=2)).groups[0].count == 2


def test_similar_templates_are_merged_unless_disabled():
    items = [item("Restart stuck worker on queue-1", n) for n in range(4)]
    items += [item("Restart stuck workers on queue-2", n + 10) for n in range(2)]
    items += [item("Grant database access to new starter", n + 20) for n in range(3)]
    merged = analyze(items)
    assert [g.count for g in merged.groups] == [6, 3]
    assert merged.groups[0].template == "restart stuck worker on <host>"  # commonest wording
    assert [len(c) for c in cluster(items, 1.0)] == [4, 3, 2]
    assert [g.count for g in analyze(items, Settings(similarity=1.0)).groups] == [4, 3]


def test_since_filters_items_and_sets_the_period_start():
    items = [item("Flush cache on web-1", day, minutes=30) for day in range(0, 100, 10)]
    newest = items[-1].created_at
    report = analyze(items, since=parse_since("30d", newest))
    assert report.total_items == 4               # days 60, 70, 80, 90
    assert (report.start, report.end, report.days) == ("2026-09-30", "2026-10-30", 30.0)
    assert analyze(items, since=newest + timedelta(days=1)).total_items == 0


def test_parse_since():
    newest = datetime(2026, 11, 1, tzinfo=timezone.utc)
    assert parse_since("90d", newest) == newest - timedelta(days=90)
    assert parse_since("2W", newest) == newest - timedelta(days=14)
    assert parse_since("3m", newest) == newest - timedelta(days=3 * DAYS_PER_MONTH)
    assert parse_since("2026-08-01", newest) == datetime(2026, 8, 1, tzinfo=timezone.utc)
    with pytest.raises(ValueError, match="invalid --since"):
        parse_since("last week", newest)
