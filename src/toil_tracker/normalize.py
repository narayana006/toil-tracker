"""Turn a ticket title into a template so that repeats of the same work match.

"Disk full on db-prod-03 (92%)" and "Disk full on db-prod-11 (97%)" both become
"disk full on <host> <n>%".
"""

from __future__ import annotations

import re

# Order matters: the more specific patterns run first.
_REPLACEMENTS: tuple[tuple[re.Pattern[str], str], ...] = tuple(
    (re.compile(pattern, re.I), replacement)
    for pattern, replacement in (
        (r"https?://\S+", "<url>"),
        (r"\b[\w.+-]+@[\w-]+(\.[\w-]+)+\b", "<email>"),
        (r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b", "<id>"),
        (r"\b\d{1,3}(\.\d{1,3}){3}(/\d{1,2})?\b", "<ip>"),
        (r"\b\d{4}-\d{2}-\d{2}([t ]\d{2}:\d{2}(:\d{2})?z?)?\b", "<date>"),
        (r"\b\d{1,2}:\d{2}(:\d{2})?\b", "<time>"),
        (r"\b[a-z0-9-]+(\.[a-z0-9-]+)*\.(com|net|org|io|dev|cloud|internal|local)\b", "<host>"),
        (r"\b(?=[a-z0-9.-]*\d)[a-z][a-z0-9]*([-.][a-z0-9]+)+\b", "<host>"),  # web-01, db3.prod.internal
        (r"\b[a-z]+\d+\b", "<host>"),                                        # node7
        (r"\b(?=[0-9a-f]*\d)(?=[0-9a-f]*[a-f])[0-9a-f]{7,}\b", "<id>"),      # commit / object ids
        (r"#?\b\d+([.,]\d+)*\b", "<n>"),
    )
)
_REF_RE = re.compile(r"\[[A-Za-z]+-\d+\]|\b[A-Z]{2,10}-\d+\b")
_PUNCTUATION_RE = re.compile(r"[^\w<>%/ -]+")
_SPACE_RE = re.compile(r"\s+")


def normalize_title(title: str) -> str:
    """Lower-case ``title`` and replace the parts that vary between repeats."""
    # Ticket references are case-sensitive (OPS-123), so handle them before lower-casing.
    text = _REF_RE.sub(" <ref> ", title).lower()
    for pattern, replacement in _REPLACEMENTS:
        text = pattern.sub(replacement, text)
    text = _PUNCTUATION_RE.sub(" ", text)
    text = re.sub(r"(<\w+>)(\s+\1)+", r"\1", _SPACE_RE.sub(" ", text))  # "<host> <host>" -> "<host>"
    return text.strip(" -/")
