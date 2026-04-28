import os
import subprocess
import sys
from datetime import datetime, timedelta

from .dates import parse_date_arg, parse_date_heading
from .store import (
    DEVLOG,
    find_last_subsection,
    find_subsection,
    parse_sections,
    parse_subsections,
    read_lines,
)


def cmd_date(arg):
    target = parse_date_arg(arg)
    target_heading = target.strftime("## %B %-d, %Y")

    sections = parse_sections(read_lines())
    for heading, content in sections:
        if heading == target_heading:
            print(heading)
            print("".join(content).rstrip())
            return

    sys.exit(f"No entry for {target.strftime('%B %-d, %Y')}")


def cmd_find(term):
    term_lower = term.lower()
    sections = parse_sections(read_lines())
    found = False

    for heading, content in sections:
        subs = parse_subsections(content)
        matching = [
            (title, body) for title, body in subs
            if term_lower in (title + "\n" + "".join(body)).lower()
        ]
        if not matching:
            continue
        if found:
            print()
        print(heading)
        for title, body in matching:
            print(title)
            body_text = "".join(body).rstrip()
            if body_text:
                print(body_text)
        found = True

    if not found:
        sys.exit(f"No entries matching '{term}'")


def _ensure_repo():
    repo = os.path.dirname(DEVLOG)
    if not os.path.isdir(os.path.join(repo, ".git")):
        sys.exit("No git repo at devlog data dir")
    return repo


def cmd_log(n=20):
    repo = _ensure_repo()
    subprocess.run(
        ["git", "-C", repo, "log", f"-{n}", "--oneline"],
        check=True,
    )


def cmd_diff(ref="HEAD"):
    repo = _ensure_repo()
    subprocess.run(
        ["git", "-C", repo, "show", ref],
        check=True,
    )


def cmd_exists(date_arg, title):
    target = parse_date_arg(date_arg)
    target_heading = target.strftime("## %B %-d, %Y")
    lines = read_lines()
    if find_subsection(lines, target_heading, title) is None:
        sys.exit(1)


def cmd_last():
    lines = read_lines()
    found = find_last_subsection(lines)
    if found is None:
        sys.exit("No entries")
    _, sub_start, sub_end = found
    print("".join(lines[sub_start:sub_end]).rstrip())


def cmd_list():
    sections = parse_sections(read_lines())
    found = False
    for heading, content in sections:
        subs = parse_subsections(content)
        if not subs:
            continue
        if found:
            print()
        print(heading)
        for title, _ in subs:
            print(title)
        found = True
    if not found:
        print("No entries")


def cmd_recent(n_days):
    cutoff = datetime.now() - timedelta(days=n_days)

    sections = parse_sections(read_lines())
    found = False

    for heading, content in sections:
        dt = parse_date_heading(heading)
        if dt is None or dt < cutoff:
            continue
        if found:
            print()
        print(heading)
        print("".join(content).rstrip())
        found = True

    if not found:
        print(f"No entries in the last {n_days} days")
