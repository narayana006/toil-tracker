"""Group repetitive work, estimate the hours it costs and rank it."""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta
from difflib import SequenceMatcher

from .loader import WorkItem
from .normalize import normalize_title

DAYS_PER_MONTH = 30.44
_SINCE_RE = re.compile(r"^(\d+)([dwm])$", re.I)
_UNIT_DAYS = {"d": 1, "w": 7, "m": DAYS_PER_MONTH}


@dataclass
class Settings:
    ticket_minutes: float = 30.0   # assumed effort for a ticket with no recorded time
    page_minutes: float = 45.0     # assumed effort for a page with no recorded time
    min_count: int = 3             # occurrences needed before work counts as repetitive
    similarity: float = 0.8        # how alike two title templates must be to be merged


@dataclass
class ToilGroup:
    template: str
    example: str                # most common original title in the group
    count: int
    tickets: int
    pages: int
    hours: float
    hours_per_month: float
    estimated_share: float      # share of the hours that come from assumed, not recorded, effort
    people: int
    first_seen: str
    last_seen: str
    items_per_month: float


@dataclass
class ToilReport:
    start: str | None
    end: str | None
    days: float
    months: float
    total_items: int
    total_hours: float
    repetitive_items: int
    repetitive_hours: float
    one_off_items: int
    one_off_hours: float
    groups: list[ToilGroup] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


def parse_since(value: str, newest: datetime) -> datetime:
    """``90d`` / ``12w`` / ``3m`` count back from ``newest``; otherwise an ISO date."""
    match = _SINCE_RE.match(value.strip())
    if match:
        return newest - timedelta(days=int(match.group(1)) * _UNIT_DAYS[match.group(2).lower()])
    try:
        parsed = datetime.fromisoformat(value.strip())
    except ValueError as error:
        raise ValueError(f"invalid --since value {value!r}: use e.g. 90d, 12w, 3m or 2026-08-01") from error
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=newest.tzinfo)


def effort_minutes(item: WorkItem, settings: Settings) -> float:
    if item.minutes is not None:
        return item.minutes
    return settings.page_minutes if item.kind == "page" else settings.ticket_minutes


def cluster(items: list[WorkItem], similarity: float) -> list[list[WorkItem]]:
    """Group items by title template, then merge templates that are nearly identical.

    Templates are visited from most to least common and each joins the first
    existing cluster whose template is at least ``similarity`` alike (word-level
    ``difflib`` ratio), so the commonest wording names the cluster.
    """
    by_template: dict[str, list[WorkItem]] = {}
    for item in items:
        by_template.setdefault(normalize_title(item.title), []).append(item)

    clusters: list[tuple[list[str], list[WorkItem]]] = []
    for template, members in sorted(by_template.items(), key=lambda kv: (-len(kv[1]), kv[0])):
        words = template.split()
        for cluster_words, cluster_members in clusters:
            if similarity < 1 and SequenceMatcher(None, cluster_words, words).ratio() >= similarity:
                cluster_members.extend(members)
                break
        else:
            clusters.append((words, list(members)))
    return [members for _, members in clusters]


def analyze(items: list[WorkItem], settings: Settings | None = None,
            since: datetime | None = None) -> ToilReport:
    settings = settings or Settings()
    if since is not None:
        items = [item for item in items if item.created_at >= since]
    if not items:
        return ToilReport(None, None, 0.0, 0.0, 0, 0.0, 0, 0.0, 0, 0.0)

    newest = max(item.created_at for item in items)
    start = since or min(item.created_at for item in items)
    days = max(1.0, (newest - start).total_seconds() / 86400)
    months = days / DAYS_PER_MONTH

    groups: list[ToilGroup] = []
    one_off_items, one_off_minutes = 0, 0.0
    for members in cluster(items, settings.similarity):
        minutes = sum(effort_minutes(m, settings) for m in members)
        if len(members) < settings.min_count:
            one_off_items += len(members)
            one_off_minutes += minutes
            continue
        assumed = sum(effort_minutes(m, settings) for m in members if m.minutes is None)
        templates = Counter(normalize_title(m.title) for m in members)
        template = min(templates, key=lambda t: (-templates[t], t))
        titles = Counter(m.title for m in members if normalize_title(m.title) == template)
        example = min(titles, key=lambda t: (-titles[t], t))
        pages = sum(1 for m in members if m.kind == "page")
        groups.append(ToilGroup(
            template=template, example=example, count=len(members),
            tickets=len(members) - pages, pages=pages,
            hours=round(minutes / 60, 1),
            hours_per_month=round(minutes / 60 / months, 1),
            estimated_share=round(assumed / minutes, 2) if minutes else 0.0,
            people=len({m.assignee for m in members if m.assignee}),
            first_seen=min(m.created_at for m in members).date().isoformat(),
            last_seen=max(m.created_at for m in members).date().isoformat(),
            items_per_month=round(len(members) / months, 1),
        ))
    # Rank by the time automation would give back; ties go to the more frequent group.
    groups.sort(key=lambda g: (-g.hours_per_month, -g.count, g.template))

    repetitive_hours = sum(g.hours for g in groups)
    return ToilReport(
        start=start.date().isoformat(), end=newest.date().isoformat(),
        days=round(days, 1), months=round(months, 2),
        total_items=len(items),
        total_hours=round(repetitive_hours + one_off_minutes / 60, 1),
        repetitive_items=sum(g.count for g in groups),
        repetitive_hours=round(repetitive_hours, 1),
        one_off_items=one_off_items, one_off_hours=round(one_off_minutes / 60, 1),
        groups=groups,
    )
