import os
import re
import subprocess
import sys
import tempfile
from datetime import datetime

from .dates import parse_date_arg, today_heading
from .store import (
    DATE_PAT,
    SUB_PAT,
    TITLE_PAT,
    find_last_subsection,
    find_subsection,
    git_snapshot,
    read_lines,
    write_lines,
    write_lock,
)


def _title_text(title_line):
    """Extract bare title from a '### [HH:MM] Title' line."""
    m = TITLE_PAT.match(title_line.rstrip())
    return m.group(1) if m else title_line.rstrip()


def _resolve_target(lines, date_arg, title):
    """Locate target subsection. If date+title given, find that one.
    Otherwise return the newest. Returns (date_idx, sub_start, sub_end)."""
    if date_arg or title:
        if not (date_arg and title):
            sys.exit("--date and --title must be used together")
        target = parse_date_arg(date_arg)
        target_heading = target.strftime("## %B %-d, %Y")
        found = find_subsection(lines, target_heading, title)
        if found is None:
            sys.exit(f"No subsection '{title}' under {target_heading}")
        return found
    found = find_last_subsection(lines)
    if found is None:
        sys.exit("No entries")
    return found


def build_block(title, body):
    lines = []
    if title:
        ts = datetime.now().strftime("%H:%M")
        lines += [f"### [{ts}] {title}\n", "\n"]
    if body:
        for line in body.strip().splitlines():
            lines.append(line + "\n")
        lines.append("\n")
    return lines


def insert_entry(title, body):
    with write_lock():
        lines = read_lines()
        today = today_heading()

        if title and find_subsection(lines, today, title) is not None:
            sys.exit(
                f"Subsection '{title}' already exists under {today}. "
                f"Use a different title or `devlog amend`/`addend`."
            )

        block = build_block(title, body)

        today_idx = next((i for i, l in enumerate(lines) if l.rstrip() == today), None)

        if today_idx is not None:
            pos = today_idx + 1
            if pos < len(lines) and not lines[pos].strip():
                pos += 1
            lines = lines[:pos] + block + lines[pos:]
        else:
            first_date = next((i for i, l in enumerate(lines) if DATE_PAT.match(l.rstrip())), None)
            section = [today + "\n", "\n"] + block
            if first_date is not None:
                lines = lines[:first_date] + section + lines[first_date:]
            else:
                title_line = next((i for i, l in enumerate(lines) if l.startswith("# ")), 0)
                lines = lines[:title_line + 1] + ["\n"] + section + lines[title_line + 1:]

        write_lines(lines)
        git_snapshot(f"add: {title}")
    print(f"Entry added under {today}")


def cmd_edit(date_arg=None, title=None):
    # Lock is held for the duration of the editor session so that a
    # concurrent write can't shift line numbers under us. Editor sessions
    # are interactive so other devlog writers will block — acceptable
    # for a solo-user tool.
    with write_lock():
        lines = read_lines()
        _, sub_start, sub_end = _resolve_target(lines, date_arg, title)

        editor = os.environ.get("EDITOR", "vim")
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as tf:
            tf.writelines(lines[sub_start:sub_end])
            tmp_path = tf.name

        try:
            subprocess.run([editor, tmp_path], check=True)
            with open(tmp_path) as f:
                new_lines = f.readlines()
        finally:
            os.unlink(tmp_path)

        while new_lines and not new_lines[-1].strip():
            new_lines.pop()
        if not new_lines:
            sys.exit("Edit aborted: empty result")
        new_lines.append("\n")

        lines = lines[:sub_start] + new_lines + lines[sub_end:]
        write_lines(lines)
        git_snapshot(f"edit: {_title_text(new_lines[0])}")
    print(f"Edited: {new_lines[0].rstrip()}")


def cmd_amend(new_text, date_arg=None, title=None):
    with write_lock():
        lines = read_lines()
        _, sub_start, sub_end = _resolve_target(lines, date_arg, title)
        title_line = lines[sub_start]
        new_body = ["\n"]
        for line in new_text.strip().splitlines():
            new_body.append(line + "\n")
        new_body.append("\n")
        lines = lines[:sub_start] + [title_line] + new_body + lines[sub_end:]
        write_lines(lines)
        git_snapshot(f"amend: {_title_text(title_line)}")
    print(f"Amended: {title_line.rstrip()}")


def cmd_addend(new_text, date_arg=None, title=None):
    with write_lock():
        lines = read_lines()
        _, sub_start, sub_end = _resolve_target(lines, date_arg, title)
        title_line = lines[sub_start]
        insert_pos = sub_end
        while insert_pos > sub_start + 1 and not lines[insert_pos - 1].strip():
            insert_pos -= 1
        addend = ["\n"]
        for line in new_text.strip().splitlines():
            addend.append(line + "\n")
        addend.append("\n")
        lines = lines[:insert_pos] + addend + lines[insert_pos:]
        write_lines(lines)
        git_snapshot(f"addend: {_title_text(title_line)}")
    print(f"Added to: {title_line.rstrip()}")


def cmd_retitle(date_arg, old_title, new_title):
    target = parse_date_arg(date_arg)
    target_heading = target.strftime("## %B %-d, %Y")
    with write_lock():
        lines = read_lines()
        if not any(l.rstrip() == target_heading for l in lines):
            sys.exit(f"No section for {target_heading}")
        found = find_subsection(lines, target_heading, old_title)
        if found is None:
            sys.exit(f"No subsection '{old_title}' under {target_heading}")
        _, sub_start, _ = found
        old_line = lines[sub_start].rstrip()
        ts_match = re.match(r"^### \[(\d{2}:\d{2})\] ", old_line)
        if ts_match:
            new_line = f"### [{ts_match.group(1)}] {new_title}\n"
        else:
            new_line = f"### {new_title}\n"
        lines[sub_start] = new_line
        write_lines(lines)
        git_snapshot(f"retitle: {old_title} -> {new_title}")
    print(f"Retitled: {old_title} -> {new_title}")


def cmd_rm(date_arg, title, dry_run=False):
    target = parse_date_arg(date_arg)
    target_heading = target.strftime("## %B %-d, %Y")

    if dry_run:
        return _rm_impl(target_heading, title, dry_run=True)
    with write_lock():
        return _rm_impl(target_heading, title, dry_run=False)


def _rm_impl(target_heading, title, dry_run):
    lines = read_lines()

    if not any(l.rstrip() == target_heading for l in lines):
        sys.exit(f"No section for {target_heading}")

    found = find_subsection(lines, target_heading, title)
    if found is None:
        sys.exit(f"No subsection '{title}' under {target_heading}")
    date_idx, sub_start, sub_end = found

    section_end = len(lines)
    for i in range(date_idx + 1, len(lines)):
        if DATE_PAT.match(lines[i].rstrip()):
            section_end = i
            break

    new_lines = lines[:sub_start] + lines[sub_end:]
    new_section_end = section_end - (sub_end - sub_start)
    has_sub = any(SUB_PAT.match(new_lines[i]) for i in range(date_idx + 1, new_section_end))
    drops_section = not has_sub
    if drops_section:
        new_lines = new_lines[:date_idx] + new_lines[new_section_end:]

    if dry_run:
        print(f"Would remove '{title}' from {target_heading}")
        if drops_section:
            print(f"Would drop empty date section {target_heading}")
        print("--- subsection content ---")
        print("".join(lines[sub_start:sub_end]).rstrip())
        return

    write_lines(new_lines)
    git_snapshot(f"rm: {title}")
    print(f"Removed '{title}' from {target_heading}")
