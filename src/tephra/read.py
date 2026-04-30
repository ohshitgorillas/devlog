"""Read-only commands: show, find, recent, list, last, exists, log, diff."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta

from .dates import parse_date_arg
from .related import find_related_line, split_related_links
from .store import (
    Entry,
    RELATED_PAT,
    find_entry,
    parse_entries,
    read_default_folder,
    read_lines,
    topic_path,
    vault_dir,
)
from .topics import list_folders, list_topics, validate_topic


@dataclass
class HydratedEntry:
    """An ``Entry`` plus the body lines belonging to it."""

    entry: Entry
    body: list[str]
    folder: str | None = None


def _hydrate(
    topic: str, lines: list[str], folder: str | None
) -> list[HydratedEntry]:
    return [
        HydratedEntry(e, lines[e.start + 1 : e.end], folder)
        for e in parse_entries(topic, lines)
    ]


def _sort_key(h: HydratedEntry) -> tuple[str, str]:
    return (h.entry.date, h.entry.time or "")


def _resolve_scope(
    folder: str | None, topic: str | None
) -> list[tuple[str | None, str]]:
    """Expand ``(folder, topic)`` into a list of ``(folder, topic)`` pairs.

    With a topic, scope is that one topic in the resolved folder. Without
    a topic, scope is all topics in the default folder.
    """
    if topic is not None:
        return [(folder, topic)]
    default = read_default_folder()
    return [(default, t) for t in list_topics(default)]


def _all_entries(
    folder: str | None, topic: str | None
) -> list[HydratedEntry]:
    """Return entries for the resolved scope, sorted newest first."""
    out: list[HydratedEntry] = []
    for f, t in _resolve_scope(folder, topic):
        path = topic_path(t, f)
        if not os.path.isfile(path):
            continue
        out.extend(_hydrate(t, read_lines(path), f))
    out.sort(key=_sort_key, reverse=True)
    return out


def _body_without_related(body: list[str]) -> list[str]:
    idx = find_related_line(body)
    if idx is None:
        return body
    return body[:idx]


def _related_links(body: list[str]) -> list[str]:
    idx = find_related_line(body)
    if idx is None:
        return []
    m = RELATED_PAT.match(body[idx])
    if not m:
        return []
    return split_related_links(m.group(1))


def _entry_label(h: HydratedEntry) -> str:
    if h.folder:
        return f"{h.folder}:{h.entry.topic}"
    return h.entry.topic


def _entry_dict(h: HydratedEntry) -> dict:
    return {
        "folder": h.folder,
        "topic": h.entry.topic,
        "date": h.entry.date,
        "time": h.entry.time,
        "title": h.entry.title,
        "body": "".join(_body_without_related(h.body)).strip(),
        "related": _related_links(h.body),
    }


def _print_entry(h: HydratedEntry) -> None:
    ts = f" ({h.entry.time})" if h.entry.time else ""
    print(f"[{_entry_label(h)}] ## {h.entry.date}{ts} — {h.entry.title}")
    text = "".join(h.body).rstrip()
    if text:
        print(text)


def _validate_scope(folder: str | None, topic: str | None) -> None:
    """Validate folder/topic pair if topic is specified."""
    if topic is None:
        return
    validate_topic(folder, topic)


def cmd_show(
    date_arg: str, folder: str | None, topic: str | None, json_out: bool
) -> None:
    """Print all entries on a given date (across topics, or one topic)."""
    _validate_scope(folder, topic)
    target = parse_date_arg(date_arg)
    matches = [h for h in _all_entries(folder, topic) if h.entry.date == target]
    if json_out:
        print(json.dumps([_entry_dict(h) for h in matches], indent=2))
        return
    if not matches:
        sys.exit(f"No entries on {target}")
    for i, h in enumerate(matches):
        if i > 0:
            print()
        _print_entry(h)


def _matches_find(h: HydratedEntry, term_lower: str, since: str | None) -> bool:
    """Predicate for ``cmd_find``: term substring match within optional date window."""
    if since is not None and h.entry.date < since:
        return False
    haystack = (h.entry.title + "\n" + "".join(h.body)).lower()
    return term_lower in haystack


def cmd_find(
    term: str,
    folder: str | None,
    topic: str | None,
    json_out: bool,
    since: str | None,
) -> None:
    """Print entries whose title or body contains ``term`` (case-insensitive)."""
    _validate_scope(folder, topic)
    term_lower = term.lower()
    matches = [
        h for h in _all_entries(folder, topic) if _matches_find(h, term_lower, since)
    ]
    if json_out:
        print(json.dumps([_entry_dict(h) for h in matches], indent=2))
        return
    if not matches:
        sys.exit(f"No entries matching '{term}'")
    for i, h in enumerate(matches):
        if i > 0:
            print()
        _print_entry(h)


def cmd_recent(
    days: int, folder: str | None, topic: str | None, json_out: bool
) -> None:
    """Print entries from the last ``days`` days."""
    _validate_scope(folder, topic)
    cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    matches = [h for h in _all_entries(folder, topic) if h.entry.date >= cutoff]
    if json_out:
        print(json.dumps([_entry_dict(h) for h in matches], indent=2))
        return
    if not matches:
        print(f"No entries in the last {days} days")
        return
    for i, h in enumerate(matches):
        if i > 0:
            print()
        _print_entry(h)


def cmd_list(folder: str | None, topic: str | None, json_out: bool) -> None:
    """Print all entry headings (no bodies)."""
    _validate_scope(folder, topic)
    entries = _all_entries(folder, topic)
    if json_out:
        out = [
            {
                "folder": h.folder,
                "topic": h.entry.topic,
                "date": h.entry.date,
                "time": h.entry.time,
                "title": h.entry.title,
            }
            for h in entries
        ]
        print(json.dumps(out, indent=2))
        return
    if not entries:
        print("No entries")
        return
    for h in entries:
        ts = f" ({h.entry.time})" if h.entry.time else ""
        print(f"[{_entry_label(h)}] {h.entry.date}{ts} — {h.entry.title}")


def cmd_last(folder: str | None, topic: str | None, json_out: bool) -> None:
    """Print the newest entry (across topics, or one topic)."""
    _validate_scope(folder, topic)
    entries = _all_entries(folder, topic)
    if not entries:
        sys.exit("No entries")
    h = entries[0]
    if json_out:
        print(json.dumps(_entry_dict(h), indent=2))
        return
    _print_entry(h)


def cmd_exists(
    folder: str | None, topic: str, date_arg: str, title: str
) -> None:
    """Exit 0 if the entry exists, 1 otherwise."""
    validate_topic(folder, topic)
    date = parse_date_arg(date_arg)
    path = topic_path(topic, folder)
    if not os.path.isfile(path):
        sys.exit(1)
    lines = read_lines(path)
    if find_entry(topic, lines, date, title) is None:
        sys.exit(1)


def _ensure_repo() -> str:
    repo = vault_dir()
    if not os.path.isdir(os.path.join(repo, ".git")):
        sys.exit(f"No git repo in vault {repo}")
    return repo


def cmd_log(n: int) -> None:
    """Print the last ``n`` commits from the vault repo."""
    repo = _ensure_repo()
    subprocess.run(["git", "-C", repo, "log", f"-{n}", "--oneline"], check=True)


def cmd_diff(ref: str) -> None:
    """``git show REF`` for the vault repo."""
    repo = _ensure_repo()
    subprocess.run(["git", "-C", repo, "show", ref], check=True)
