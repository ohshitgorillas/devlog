"""Parse, format, and validate ``[[Topic#anchor]]`` related-entry links."""

from __future__ import annotations

import os
import re
import sys

from .store import (
    RELATED_PAT,
    parse_entries,
    read_default_folder,
    read_lines,
    topic_path,
)
from .topics import list_topics

_ANCHOR_PAT = re.compile(r"^(\d{4}-\d{2}-\d{2})(?: (\d{2}:\d{2}))? — (.+)$")


def format_anchor(date: str, time: str | None, title: str) -> str:
    """Return the heading anchor text for a (date, time, title) triple."""
    ts = f" {time}" if time else ""
    return f"{date}{ts} — {title}"


def format_heading(date: str, time: str | None, title: str) -> str:
    """Return the full ``## ...`` heading line (no trailing newline)."""
    return f"## {format_anchor(date, time, title)}"


def parse_link_arg(arg: str) -> tuple[str | None, str, str, str | None, str]:
    """Parse a user-supplied ref into ``(folder, topic, date, time, title)``.

    Forms:
      - ``Topic#anchor``           → (default_folder, "Topic", ...)
      - ``Folder:Topic#anchor``    → ("Folder", "Topic", ...)
    """
    if "#" not in arg:
        sys.exit(
            f"Invalid related ref '{arg}': expected '[Folder:]Topic#YYYY-MM-DD — Title'"
        )
    head, anchor = arg.split("#", 1)
    head = head.strip()
    anchor = anchor.strip()
    folder: str | None
    if ":" in head:
        folder, topic = head.split(":", 1)
        folder = folder.strip()
        topic = topic.strip()
        if not folder or not topic:
            sys.exit(
                f"Invalid related ref '{arg}': both folder and topic required "
                f"(form: 'Folder:Topic#anchor')"
            )
    else:
        folder = read_default_folder()
        topic = head
    m = _ANCHOR_PAT.match(anchor)
    if not m:
        sys.exit(
            f"Invalid related ref '{arg}': anchor must be 'YYYY-MM-DD [HH:MM] — Title'"
        )
    return folder, topic, m.group(1), m.group(2), m.group(3)


def validate_link(
    folder: str | None, topic: str, date: str, time: str | None, title: str
) -> str:
    """Confirm entry exists in ``folder``/``topic``. Returns resolved anchor."""
    topics = list_topics(folder)
    label = f"{folder}:{topic}" if folder else topic
    if topic not in topics:
        sys.exit(f"Related ref: unknown topic '{label}'")
    path = topic_path(topic, folder)
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
        + f" in topic '{label}'"
    )


def _format_link(folder: str | None, topic: str, anchor: str) -> str:
    head = f"{folder}:{topic}" if folder else topic
    return f"[[{head}#{anchor}]]"


def format_related_line(refs: list[str]) -> str:
    """Build the ``**Related:** [[...]], [[...]]`` line (no newline)."""
    links = []
    for ref in refs:
        folder, topic, date, time, title = parse_link_arg(ref)
        anchor = validate_link(folder, topic, date, time, title)
        links.append(_format_link(folder, topic, anchor))
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
