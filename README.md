# toil-tracker

Measure operational toil from tickets and pages and rank the best candidates for automation.

> **Project status: planning. There is no working code in this repository yet.**
> This README describes what the project will do. Nothing below can be installed or run today.
> Features are ticked off in the checklist as they are built.

## What it is

A command-line tool.

**The problem it solves:** Everyone agrees toil should be reduced, but without numbers it never wins prioritisation.

## Who it is for

SRE and platform leads who need evidence to prioritise automation work.

## How it will work

1. You import tickets and pages for a period.
2. The tool groups repetitive work and estimates the time each group costs.
3. It ranks the groups by time that automation would save and writes a report.

## Planned features

Unticked items are not built yet.

- [ ] Imports tickets and pages from common trackers or CSV
- [ ] Groups repetitive work into categories
- [ ] Estimates hours spent per category per month
- [ ] Ranks automation candidates by time saved
- [ ] Quarterly toil report

## Planned usage

This is the intended interface, shown so you can judge the design. **It does not work yet**, and names may change before the first release.

```bash
toil-tracker analyze tickets.csv --since 90d
```

## Contributing

Feedback on the design is the most useful contribution right now. Open an issue to suggest a feature, question an approach or describe your use case. Code contributions are welcome once the first version lands.

## License

[MIT](LICENSE)
