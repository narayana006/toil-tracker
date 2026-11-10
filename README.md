# toil-tracker

Turns a CSV export of tickets and pages into numbers you can prioritise with: which repetitive work costs the most hours per month, ranked as automation candidates.

**Status:** v0.1.0. Working today: CSV import, grouping of repetitive work by normalised title, hours per group per month, ranked automation candidates, Markdown and JSON reports. Not built yet: direct import from trackers (Jira, PagerDuty and so on) and a quarter-over-quarter report.

## Why

Everyone agrees toil should be reduced, but "we restart that worker a lot" does not win a planning argument. "Restarting stuck workers cost us 3.3 hours a month last quarter" has a better chance.

## Install

Python 3.10 or newer. No runtime dependencies.

```bash
git clone https://github.com/narayana006/toil-tracker.git
cd toil-tracker
pip install .
```

## Quick start

`examples/tickets.csv` holds 102 synthetic tickets and pages. Analyse the last 90 days and show the top five groups:

```bash
toil-tracker analyze examples/tickets.csv --since 90d --top 5
```

```markdown
# Toil report

Period: 2026-08-08 to 2026-11-06 (90 days, 2.96 months).

- Items analysed: 85 (63.3 hours)
- Repetitive work: 79 items in 7 groups, 47.9 hours (76% of all hours, 16.2 hours per month)
- One-off work (fewer than 3 similar items): 6 items, 15.4 hours

## Automation candidates

Ranked by hours per month, which is the time automating the group would give back.

| Rank | Work | Items | Per month | Hours | Hours / month | Hours / year | People |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | Disk full on db-prod-04 (97%) | 22 | 7.4 | 11.8 | 4 | 48 | 5 |
| 2 | Rotate TLS certificate for pay.example.com | 13 | 4.4 | 11.8 | 4 | 48 | 2 |
| 3 | Restart stuck worker on queue-1 | 13 | 4.4 | 9.8 | 3.3 | 40 | 4 |
| 4 | Deploy failed: pipeline #4198 stuck at integration tests | 9 | 3 | 6.3 | 2.1 | 25 | 5 |
| 5 | Grant read access to billing database for a.kumar@example.com | 12 | 4.1 | 4.2 | 1.4 | 17 | 5 |

2 more groups (4 hours) not shown; use --top to see them.

## Details

1. **Disk full on db-prod-04 (97%)**
   - Pattern: `disk full on <host> <n>%`
   - 22 pages; first seen 2026-08-12, last seen 2026-11-06
   - 11.8 hours in the period; 32% of the hours assumed, the rest recorded
2. **Rotate TLS certificate for pay.example.com**
   - Pattern: `rotate tls certificate for <host>`
   - 13 tickets; first seen 2026-08-12, last seen 2026-11-04
   - 11.8 hours in the period; all effort from recorded time
3. **Restart stuck worker on queue-1**
   - Pattern: `restart stuck worker on <host>`
   - 13 pages; first seen 2026-08-11, last seen 2026-11-02
   - 9.8 hours in the period; all effort assumed, none recorded
4. **Deploy failed: pipeline #4198 stuck at integration tests**
   - Pattern: `deploy failed pipeline <n> stuck at integration tests`
   - 9 tickets; first seen 2026-08-12, last seen 2026-10-31
   - 6.3 hours in the period; all effort from recorded time
5. **Grant read access to billing database for a.kumar@example.com**
   - Pattern: `grant read access to billing database for <email>`
   - 12 tickets; first seen 2026-08-20, last seen 2026-11-06
   - 4.2 hours in the period; all effort from recorded time

Items without recorded time are counted as 30 minutes per ticket and 45 minutes per page.
```

## Input format

A CSV file with a header row. Only `title` and `created_at` are required.

| Column | Required | Meaning |
| --- | --- | --- |
| `title` | yes | What the work was. Also accepted: `summary`, `subject`, `description`, `name` |
| `created_at` | yes | ISO 8601 date or timestamp (`2026-09-01`, `2026-09-01T14:00:00Z`), or `DD/MM/YYYY`. No offset means UTC. Also accepted: `created`, `opened_at`, `triggered_at`, `date` |
| `minutes_spent` | no | Recorded effort in minutes. Also accepted: `time_spent_minutes`, `minutes`, `effort_minutes` |
| `hours_spent` | no | Recorded effort in hours, used when there is no minutes value. Also accepted: `time_spent_hours`, `hours`, `effort_hours` |
| `type` | no | `page`, `incident`, `alert`, `pagerduty` or `opsgenie` mark a page; anything else is a ticket. Also accepted: `kind`, `issue_type`, `source` |
| `assignee` | no | Used to count how many people did the work. Also accepted: `owner`, `assigned_to`, `responder` |
| `id` | no | Kept for reference. Also accepted: `key`, `ticket`, `number` |

Column names are case-insensitive, spaces and underscores are interchangeable (`Issue Type` works), and other columns are ignored. The first rows of the example:

```csv
id,created_at,type,title,minutes_spent,assignee
OPS-2101,2026-07-21T11:05:00Z,page,Restart stuck worker on queue-4,,dmitri
OPS-2102,2026-07-22T17:13:00Z,ticket,Rotate TLS certificate for admin.example.com,60,ben
OPS-2103,2026-07-24T15:29:00Z,page,Restart stuck workers on queue-2,,ben
```

## How it works

1. **Normalise titles.** Each title is lower-cased and its variable parts are replaced with placeholders: `<host>` (names containing a number such as `db-prod-03` or `queue-4`, and domain names), `<n>`, `<email>`, `<ip>`, `<url>`, `<date>`, `<time>`, `<id>` (UUIDs and hex ids) and `<ref>` (ticket keys such as `OPS-123`). "Disk full on db-prod-03 (92%)" and "Disk full on logs-11 (97%)" both become `disk full on <host> <n>%`.
2. **Group.** Items with the same pattern form a group. Patterns that are nearly the same, word for word, are merged (`--similarity`, default 0.8), so "Restart stuck worker on ..." and "Restart stuck workers on ..." end up together.
3. **Estimate hours.** Recorded time is used where the export has it. Items without it are counted as 30 minutes per ticket and 45 minutes per page (`--ticket-minutes`, `--page-minutes`). The report says, per group, how much of the figure is assumed.
4. **Rank.** Groups with at least 3 items (`--min-count`) count as repetitive and are ranked by hours per month: total hours divided by the length of the period in months. Everything else is reported as one-off work.

## Options

```text
toil-tracker analyze [--since WHEN] [--format {markdown,json}] [-o PATH] [--top N]
                     [--min-count N] [--similarity RATIO] [--ticket-minutes MIN]
                     [--page-minutes MIN] FILE
```

- `FILE`: the CSV, or `-` for stdin.
- `--since WHEN`: `90d`, `12w` or `3m` counts back from the newest item in the file (not from today, so an old export gives the same result whenever you run it). A date such as `2026-08-01` is also accepted. Without `--since`, the period runs from the oldest item to the newest.
- `--format json`: every group with all its figures, for spreadsheets or dashboards.
- `-o PATH`: write the report to a file.
- `--top N`: groups shown in the Markdown report (default 10). JSON always contains all groups.
- `--similarity RATIO`: between 0 and 1; `1` turns merging off so only identical patterns group.

Exit status is 0 on success and 2 when the file cannot be read or parsed; the error names the line.

## Features

- [x] Imports tickets and pages from CSV
- [ ] Imports directly from common trackers (Jira, PagerDuty, ServiceNow)
- [x] Groups repetitive work into categories
- [x] Estimates hours spent per category per month
- [x] Ranks automation candidates by time saved
- [x] Markdown and JSON toil report for a chosen period
- [ ] Quarterly report with trend against the previous quarter

## Limitations

- The hours are only as good as the input. If your tracker does not record time spent, every figure rests on the per-ticket and per-page defaults; set them to something your team believes.
- Grouping looks at titles only. Work described with different wording each time will not group, and unrelated tickets with near-identical titles will. Check the "Pattern" line of each group before quoting its number.
- "Time saved" assumes automation removes the whole group. It ignores the cost of building and maintaining the automation.
- With a short period the per-month figures are extrapolations; a week of data scaled to a month is noisy.
- English-centric normalisation, CSV only, and no deduplication of a page and a ticket raised for the same event.

## Contributing

Issues and pull requests are welcome. Titles that normalise badly are especially useful: include the title and the pattern you expected.

```bash
pip install -e ".[dev]"
pytest
```

## Author

Built and maintained by [Narayana Vemburaj](https://github.com/narayana006).

## License

[MIT](LICENSE)
