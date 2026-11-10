"""Command-line interface: ``toil-tracker analyze tickets.csv --since 90d``."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import __version__
from .analysis import Settings, analyze, parse_since
from .loader import InputError, load_csv
from .report import to_json, to_markdown


def build_parser() -> argparse.ArgumentParser:
    defaults = Settings()
    parser = argparse.ArgumentParser(
        prog="toil-tracker",
        description="Measure toil from a tickets/pages CSV and rank automation candidates.")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)
    cmd = sub.add_parser("analyze", help="analyze a CSV of tickets and pages")
    cmd.add_argument("file", metavar="FILE", help="CSV export, or - for stdin")
    cmd.add_argument("--since", metavar="WHEN",
                     help="only items since WHEN: 90d, 12w or 3m (counted back from the newest "
                          "item in the file) or a date such as 2026-08-01")
    cmd.add_argument("--format", choices=("markdown", "json"), default="markdown",
                     help="output format (default: markdown)")
    cmd.add_argument("-o", "--output", metavar="PATH", help="write the report to PATH instead of stdout")
    cmd.add_argument("--top", type=int, default=10, metavar="N",
                     help="groups to show in the Markdown report (default: 10)")
    cmd.add_argument("--min-count", type=int, default=defaults.min_count, metavar="N",
                     help=f"similar items needed to count as repetitive (default: {defaults.min_count})")
    cmd.add_argument("--similarity", type=float, default=defaults.similarity, metavar="RATIO",
                     help="0-1; merge title patterns at least this alike, 1 disables merging "
                          f"(default: {defaults.similarity})")
    cmd.add_argument("--ticket-minutes", type=float, default=defaults.ticket_minutes, metavar="MIN",
                     help=f"assumed effort for a ticket with no recorded time (default: {defaults.ticket_minutes:g})")
    cmd.add_argument("--page-minutes", type=float, default=defaults.page_minutes, metavar="MIN",
                     help=f"assumed effort for a page with no recorded time (default: {defaults.page_minutes:g})")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not 0 < args.similarity <= 1:
        parser.error("--similarity must be greater than 0 and at most 1")
    if args.min_count < 1 or args.top < 1:
        parser.error("--min-count and --top must be at least 1")
    try:
        text = sys.stdin.read() if args.file == "-" else Path(args.file).read_text(encoding="utf-8")
        items = load_csv(text)
        since = parse_since(args.since, max(i.created_at for i in items)) if args.since and items else None
    except (OSError, UnicodeDecodeError, ValueError) as error:  # InputError is a ValueError
        print(f"toil-tracker: {args.file}: {error}", file=sys.stderr)
        return 2

    settings = Settings(ticket_minutes=args.ticket_minutes, page_minutes=args.page_minutes,
                        min_count=args.min_count, similarity=args.similarity)
    report = analyze(items, settings, since)
    rendered = to_json(report) + "\n" if args.format == "json" else to_markdown(report, settings, args.top)
    if args.output:
        Path(args.output).write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    sys.exit(main())
