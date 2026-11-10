import pytest

from toil_tracker.normalize import normalize_title


@pytest.mark.parametrize("title, expected", [
    ("Disk full on db-prod-03 (92%)", "disk full on <host> <n>%"),
    ("Disk full on logs-11 (97%)", "disk full on <host> <n>%"),
    ("[OPS-123] Restart nginx on web01", "<ref> restart nginx on <host>"),
    ("OPS-99: Restart nginx on web-2", "<ref> restart nginx on <host>"),
    ("Rotate TLS certificate for api.example.com", "rotate tls certificate for <host>"),
    ("Grant read access for j.smith@example.com", "grant read access for <email>"),
    ("Deploy failed: pipeline #4521 stuck", "deploy failed pipeline <n> stuck"),
    ("Cert expiring 2026-10-01 for 10.0.0.12", "cert expiring <date> for <ip>"),
    ("Revert commit 3f2a9bc1d on main", "revert commit <id> on main"),
    ("Job 7f9c2d1e-1b2a-4c3d-8e9f-0a1b2c3d4e5f failed at 14:02", "job <id> failed at <time>"),
    ("See https://wiki.example.com/runbook?id=3 for steps", "see <url> for steps"),
    ("Upgrade Postgres 15 to 16 on staging", "upgrade postgres <n> to <n> on staging"),
    ("  Out-of-memory   in EU-West!! ", "out-of-memory in eu-west"),
    ("Failover 3 4 5 replicas", "failover <n> replicas"),
])
def test_normalize_title(title, expected):
    assert normalize_title(title) == expected


def test_plain_words_are_left_alone():
    assert normalize_title("Payment gateway outage") == "payment gateway outage"
    assert normalize_title("Add feedback form to the decade review") == "add feedback form to the decade review"
