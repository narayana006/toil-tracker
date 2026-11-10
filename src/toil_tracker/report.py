"""Render a toil report as Markdown or JSON."""

from __future__ import annotations

import json

from .analysis import Settings, ToilReport


def to_json(report: ToilReport) -> str:
    return json.dumps(report.to_dict(), indent=2)


def _cell(text: str) -> str:
    return text.replace("|", "\\|")


def to_markdown(report: ToilReport, settings: Settings, top: int = 10) -> str:
    if report.total_items == 0:
        return "# Toil report\n\nNo tickets or pages in the selected period.\n"
    share = report.repetitive_hours / report.total_hours if report.total_hours else 0.0
    out = [
        "# Toil report",
        "",
        f"Period: {report.start} to {report.end} ({report.days:g} days, {report.months:g} months).",
        "",
        f"- Items analysed: {report.total_items} ({report.total_hours:g} hours)",
        f"- Repetitive work: {report.repetitive_items} items in {len(report.groups)} groups, "
        f"{report.repetitive_hours:g} hours ({share:.0%} of all hours, "
        f"{report.repetitive_hours / report.months:.1f} hours per month)",
        f"- One-off work (fewer than {settings.min_count} similar items): "
        f"{report.one_off_items} items, {report.one_off_hours:g} hours",
        "",
    ]
    if not report.groups:
        out.append(f"No group of similar items reached {settings.min_count} occurrences.")
        return "\n".join(out) + "\n"

    shown = report.groups[:top]
    out += [
        "## Automation candidates",
        "",
        "Ranked by hours per month, which is the time automating the group would give back.",
        "",
        "| Rank | Work | Items | Per month | Hours | Hours / month | Hours / year | People |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for rank, group in enumerate(shown, start=1):
        out.append(
            f"| {rank} | {_cell(group.example)} | {group.count} | {group.items_per_month:g} | "
            f"{group.hours:g} | {group.hours_per_month:g} | {group.hours_per_month * 12:.0f} | "
            f"{group.people or '-'} |")
    out.append("")
    if len(shown) < len(report.groups):
        rest = report.groups[top:]
        out += [f"{len(rest)} more groups ({sum(g.hours for g in rest):g} hours) not shown; "
                "use --top to see them.", ""]

    out += ["## Details", ""]
    for rank, group in enumerate(shown, start=1):
        kinds = ", ".join(f"{n} {label}{'s' if n != 1 else ''}"
                          for n, label in ((group.tickets, "ticket"), (group.pages, "page")) if n)
        if group.estimated_share == 0:
            basis = "all effort from recorded time"
        elif group.estimated_share == 1:
            basis = "all effort assumed, none recorded"
        else:
            basis = f"{group.estimated_share:.0%} of the hours assumed, the rest recorded"
        out += [
            f"{rank}. **{_cell(group.example)}**",
            f"   - Pattern: `{group.template}`",
            f"   - {kinds}; first seen {group.first_seen}, last seen {group.last_seen}",
            f"   - {group.hours:g} hours in the period; {basis}",
        ]
    out += [
        "",
        f"Items without recorded time are counted as {settings.ticket_minutes:g} minutes per ticket "
        f"and {settings.page_minutes:g} minutes per page.",
    ]
    return "\n".join(out) + "\n"
