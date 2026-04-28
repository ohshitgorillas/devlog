"""Read-only commands: show, find, recent, list, last, exists, log, diff."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timedelta
from typing import Any

from .dates import format_date_heading, parse_date_arg, parse_date_heading
from .store import (
    DEVLOG,
    find_last_subsection,
    find_subsection,
    parse_sections,
    parse_subsections,
    parse_title_line,
    read_lines,
)


def _strip_heading(heading: str) -> str:
    """'## April 27, 2026' -> 'April 27, 2026'."""
    return heading[3:] if heading.startswith("## ") else heading


def _entry_dict(
    heading: str,
    subs: list[tuple[str, list[str]]],
    with_bodies: bool = True,
) -> dict[str, Any]:
    """Build a JSON-serializable dict for one date section."""
    out_subs: list[dict[str, Any]] = []
    for title_line, body_lines in subs:
        ts, t = parse_title_line(title_line)
        sub: dict[str, Any] = {"ts": ts, "title": t}
        if with_bodies:
            sub["body"] = "".join(body_lines).strip()
        out_subs.append(sub)
    return {"date": _strip_heading(heading), "subsections": out_subs}


def cmd_date(arg: str, json_out: bool = False) -> None:
    """Print the full day section for `arg` (YYYYMMDD or MMDD)."""
    target = parse_date_arg(arg)
    target_heading = format_date_heading(target)

    sections = parse_sections(read_lines())
    for heading, content in sections:
        if heading == target_heading:
            if json_out:
                subs = parse_subsections(content)
                print(json.dumps(_entry_dict(heading, subs), indent=2))
            else:
                print(heading)
                print("".join(content).rstrip())
            return

    sys.exit(f"No entry for {target.strftime('%B %-d, %Y')}")


def _collect_matches(
    term: str,
) -> list[tuple[str, list[tuple[str, list[str]]]]]:
    """Return [(heading, [(title, body), ...]), ...] for all sections containing `term`."""
    term_lower = term.lower()
    sections = parse_sections(read_lines())
    matches: list[tuple[str, list[tuple[str, list[str]]]]] = []
    for heading, content in sections:
        subs = parse_subsections(content)
        matching = [
            (title, body)
            for title, body in subs
            if term_lower in (title + "\n" + "".join(body)).lower()
        ]
        if matching:
            matches.append((heading, matching))
    return matches


def _print_match_group(heading: str, subs: list[tuple[str, list[str]]]) -> None:
    """Print one (heading, matching subsections) group as text."""
    print(heading)
    for title, body in subs:
        print(title)
        body_text = "".join(body).rstrip()
        if body_text:
            print(body_text)


def cmd_find(term: str, json_out: bool = False) -> None:
    """Print all subsections matching `term` (case-insensitive substring)."""
    matches = _collect_matches(term)
    if json_out:
        print(json.dumps([_entry_dict(h, s) for h, s in matches], indent=2))
        return
    if not matches:
        sys.exit(f"No entries matching '{term}'")
    for i, (heading, subs) in enumerate(matches):
        if i > 0:
            print()
        _print_match_group(heading, subs)


def _ensure_repo() -> str:
    """Return the data-repo path, exiting if no .git directory exists."""
    repo = os.path.dirname(DEVLOG)
    if not os.path.isdir(os.path.join(repo, ".git")):
        sys.exit("No git repo at devlog data dir")
    return repo


def cmd_log(n: int = 20) -> None:
    """Print the last `n` commits from the data repo."""
    repo = _ensure_repo()
    subprocess.run(
        ["git", "-C", repo, "log", f"-{n}", "--oneline"],
        check=True,
    )


def cmd_diff(ref: str = "HEAD") -> None:
    """Print `git show REF` for the data repo."""
    repo = _ensure_repo()
    subprocess.run(
        ["git", "-C", repo, "show", ref],
        check=True,
    )


def cmd_exists(date_arg: str, title: str) -> None:
    """Exit 0 if a subsection exists at (date, title), else exit 1."""
    target = parse_date_arg(date_arg)
    target_heading = format_date_heading(target)
    lines = read_lines()
    if find_subsection(lines, target_heading, title) is None:
        sys.exit(1)


def cmd_last(json_out: bool = False) -> None:
    """Print the most recent subsection (heading + body)."""
    lines = read_lines()
    found = find_last_subsection(lines)
    if found is None:
        sys.exit("No entries")
    date_idx, sub_start, sub_end = found
    if json_out:
        title_line = lines[sub_start]
        ts, t = parse_title_line(title_line)
        body = "".join(lines[sub_start + 1 : sub_end]).strip()
        date = _strip_heading(lines[date_idx].rstrip())
        print(json.dumps({"date": date, "ts": ts, "title": t, "body": body}, indent=2))
        return
    print("".join(lines[sub_start:sub_end]).rstrip())


def cmd_list(json_out: bool = False) -> None:
    """Print every date heading and its subsection titles (no bodies)."""
    sections = parse_sections(read_lines())
    entries = []
    for heading, content in sections:
        subs = parse_subsections(content)
        if not subs:
            continue
        entries.append(_entry_dict(heading, subs, with_bodies=False))

    if json_out:
        print(json.dumps(entries, indent=2))
        return

    if not entries:
        print("No entries")
        return
    for i, entry in enumerate(entries):
        if i > 0:
            print()
        print(f"## {entry['date']}")
        for sub in entry["subsections"]:
            ts_part = f"[{sub['ts']}] " if sub["ts"] else ""
            print(f"### {ts_part}{sub['title']}")


def cmd_recent(n_days: int, json_out: bool = False) -> None:
    """Print all date sections within the last `n_days` (full bodies)."""
    cutoff = datetime.now() - timedelta(days=n_days)
    sections = parse_sections(read_lines())
    matches = []
    for heading, content in sections:
        dt = parse_date_heading(heading)
        if dt is None or dt < cutoff:
            continue
        subs = parse_subsections(content)
        matches.append((heading, content, subs))

    if json_out:
        print(
            json.dumps(
                [_entry_dict(h, s) for h, _, s in matches],
                indent=2,
            )
        )
        return

    if not matches:
        print(f"No entries in the last {n_days} days")
        return
    for i, (heading, content, _) in enumerate(matches):
        if i > 0:
            print()
        print(heading)
        print("".join(content).rstrip())
