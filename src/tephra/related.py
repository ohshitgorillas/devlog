"""Parse, format, and validate ``[[Topic#anchor]]`` related-entry links."""

from __future__ import annotations

import os
import re
import sys

from .store import (
    RELATED_PAT,
    parse_entries,
    read_lines,
    topic_path,
)
from .topics import list_topics

_ANCHOR_PAT = re.compile(r"^(\d{4}-\d{2}-\d{2})(?: \((\d{2}:\d{2})\))? — (.+)$")


def format_anchor(date: str, time: str | None, title: str) -> str:
    """Return the heading anchor text for a (date, time, title) triple."""
    ts = f" ({time})" if time else ""
    return f"{date}{ts} — {title}"


def format_heading(date: str, time: str | None, title: str) -> str:
    """Return the full ``## ...`` heading line (no trailing newline)."""
    return f"## {format_anchor(date, time, title)}"


def parse_link_arg(arg: str) -> tuple[str, str, str | None, str]:
    """Parse a user-supplied ``Topic#YYYY-MM-DD [(HH:MM)] — Title`` ref.

    Returns ``(topic, date, time_or_None, title)``.
    """
    if "#" not in arg:
        sys.exit(f"Invalid related ref '{arg}': expected 'Topic#YYYY-MM-DD — Title'")
    topic, anchor = arg.split("#", 1)
    topic = topic.strip()
    anchor = anchor.strip()
    m = _ANCHOR_PAT.match(anchor)
    if not m:
        sys.exit(
            f"Invalid related ref '{arg}': anchor must be "
            f"'YYYY-MM-DD [(HH:MM)] — Title'"
        )
    return topic, m.group(1), m.group(2), m.group(3)


def validate_link(topic: str, date: str, time: str | None, title: str) -> str:
    """Confirm the entry exists in ``topic.md``. Returns the resolved anchor."""
    topics = list_topics()
    if topic not in topics:
        sys.exit(f"Related ref: unknown topic '{topic}'")
    path = topic_path(topic)
    if not os.path.isfile(path):
        sys.exit(f"Related ref: topic file missing at {path}")
    lines = read_lines(path)
    for e in parse_entries(topic, lines):
        if e.date != date or e.title != title:
            continue
        if time is not None and e.time != time:
            continue
        return format_anchor(e.date, e.time, e.title)
    sys.exit(
        f"Related ref: no entry '{title}' on {date}"
        + (f" at {time}" if time else "")
        + f" in topic '{topic}'"
    )


def format_related_line(refs: list[str]) -> str:
    """Build the ``**Related:** [[...]], [[...]]`` line (no newline)."""
    links = []
    for ref in refs:
        topic, date, time, title = parse_link_arg(ref)
        anchor = validate_link(topic, date, time, title)
        links.append(f"[[{topic}#{anchor}]]")
    return "**Related:** " + ", ".join(links)


def split_related_links(value: str) -> list[str]:
    """Split a Related-line payload into individual ``[[...]]`` link strings.

    Splits on ``,`` outside of ``[[...]]`` brackets and strips whitespace.
    """
    out: list[str] = []
    depth = 0
    buf = ""
    for ch in value:
        if ch == "[":
            depth += 1
            buf += ch
        elif ch == "]":
            depth -= 1
            buf += ch
        elif ch == "," and depth == 0:
            if buf.strip():
                out.append(buf.strip())
            buf = ""
        else:
            buf += ch
    if buf.strip():
        out.append(buf.strip())
    return out


def find_related_line(body_lines: list[str]) -> int | None:
    """Return the index in ``body_lines`` of an existing Related line, or None."""
    for i, line in enumerate(body_lines):
        if RELATED_PAT.match(line):
            return i
    return None
