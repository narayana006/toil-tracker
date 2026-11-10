import io
import json
from pathlib import Path

import pytest

from toil_tracker.cli import main

EXAMPLE = str(Path(__file__).resolve().parent.parent / "examples" / "tickets.csv")


def test_example_report(capsys):
    assert main(["analyze", EXAMPLE, "--since", "90d"]) == 0
    out = capsys.readouterr().out
    assert "Period: 2026-08-08 to 2026-11-06 (90 days, 2.96 months)." in out
    assert "- Repetitive work: 79 items in 7 groups, 47.9 hours (76% of all hours" in out
    assert "| 1 | Disk full on db-prod-04 (97%) | 22 |" in out
    assert "   - Pattern: `rotate tls certificate for <host>`" in out
    assert "counted as 30 minutes per ticket and 45 minutes per page" in out


def test_json_matches_markdown_totals(capsys):
    assert main(["analyze", EXAMPLE, "--format", "json"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["total_items"] == 102
    assert data["repetitive_items"] + data["one_off_items"] == data["total_items"]
    ranked = [g["hours_per_month"] for g in data["groups"]]
    assert ranked == sorted(ranked, reverse=True)


def test_top_and_output_file(tmp_path, capsys):
    target = tmp_path / "report.md"
    assert main(["analyze", EXAMPLE, "--top", "2", "-o", str(target)]) == 0
    assert capsys.readouterr().out == ""
    text = target.read_text()
    assert "| 2 |" in text and "| 3 |" not in text
    assert "more groups" in text and "use --top to see them" in text


def test_effort_options_change_the_estimate(capsys):
    main(["analyze", EXAMPLE, "--format", "json"])
    base = json.loads(capsys.readouterr().out)["total_hours"]
    main(["analyze", EXAMPLE, "--format", "json", "--page-minutes", "90", "--ticket-minutes", "60"])
    assert json.loads(capsys.readouterr().out)["total_hours"] > base


def test_stdin_with_no_rows(monkeypatch, capsys):
    monkeypatch.setattr("sys.stdin", io.StringIO("title,created_at\n"))
    assert main(["analyze", "-", "--since", "30d"]) == 0
    assert "No tickets or pages in the selected period." in capsys.readouterr().out


def test_no_repetitive_work(monkeypatch, capsys):
    monkeypatch.setattr("sys.stdin", io.StringIO("title,created_at\nOne thing,2026-09-01\n"))
    assert main(["analyze", "-"]) == 0
    assert "No group of similar items reached 3 occurrences." in capsys.readouterr().out


def test_errors_exit_2(tmp_path, capsys):
    assert main(["analyze", str(tmp_path / "missing.csv")]) == 2
    assert main(["analyze", EXAMPLE, "--since", "whenever"]) == 2
    assert "invalid --since value 'whenever'" in capsys.readouterr().err
    with pytest.raises(SystemExit) as error:
        main(["analyze", EXAMPLE, "--similarity", "0"])
    assert error.value.code == 2
