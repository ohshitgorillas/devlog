"""Write commands: add, edit, amend, addend, retitle, rm, undo."""

from __future__ import annotations

import os
import re
import subprocess
import sys
import tempfile
from datetime import datetime

from .dates import format_date_heading, parse_date_arg, today_heading
from .store import (
    DATE_PAT,
    DEVLOG,
    SUB_PAT,
    TITLE_PAT,
    compute_outside_fence,
    find_last_subsection,
    find_section_end,
    find_subsection,
    git_snapshot,
    read_lines,
    write_lines,
    write_lock,
)


def _title_text(title_line: str) -> str:
    """Extract bare title from a '### [HH:MM] Title' line."""
    m = TITLE_PAT.match(title_line.rstrip())
    return m.group(1) if m else title_line.rstrip()


def _resolve_target(
    lines: list[str], date_arg: str | None, title: str | None
) -> tuple[int, int, int]:
    """Locate target subsection. If date+title given, find that one.
    Otherwise return the newest. Returns (date_idx, sub_start, sub_end)."""
    if date_arg or title:
        if not (date_arg and title):
            sys.exit("--date and --title must be used together")
        target = parse_date_arg(date_arg)
        target_heading = format_date_heading(target)
        found = find_subsection(lines, target_heading, title)
        if found is None:
            sys.exit(f"No subsection '{title}' under {target_heading}")
        return found
    found = find_last_subsection(lines)
    if found is None:
        sys.exit("No entries")
    return found


def build_block(title: str | None, body: str | None) -> list[str]:
    """Build a list of lines for a new subsection (title heading + body)."""
    lines: list[str] = []
    if title:
        ts = datetime.now().strftime("%H:%M")
        lines += [f"### [{ts}] {title}\n", "\n"]
    if body:
        for line in body.strip().splitlines():
            lines.append(line + "\n")
        lines.append("\n")
    return lines


def _insert_under_today(
    lines: list[str], today_idx: int, block: list[str]
) -> list[str]:
    """Insert `block` immediately under an existing today date heading."""
    pos = today_idx + 1
    if pos < len(lines) and not lines[pos].strip():
        pos += 1
    return lines[:pos] + block + lines[pos:]


def _insert_new_section(lines: list[str], section: list[str]) -> list[str]:
    """Prepend a brand-new date section above the existing latest section,
    or at the top of the file if no date sections exist yet."""
    outside = compute_outside_fence(lines)
    first_date = next(
        (
            i
            for i, line in enumerate(lines)
            if outside[i] and DATE_PAT.match(line.rstrip())
        ),
        None,
    )
    if first_date is not None:
        return lines[:first_date] + section + lines[first_date:]
    title_line = next((i for i, line in enumerate(lines) if line.startswith("# ")), 0)
    return lines[: title_line + 1] + ["\n"] + section + lines[title_line + 1 :]


def insert_entry(title: str, body: str) -> None:
    """Add a new subsection under today's date heading (creating it if needed)."""
    with write_lock():
        lines = read_lines()
        today = today_heading()

        if title and find_subsection(lines, today, title) is not None:
            sys.exit(
                f"Subsection '{title}' already exists under {today}. "
                f"Use a different title or `devlog amend`/`addend`."
            )

        block = build_block(title, body)
        outside = compute_outside_fence(lines)
        today_idx = next(
            (
                i
                for i, line in enumerate(lines)
                if outside[i] and line.rstrip() == today
            ),
            None,
        )

        if today_idx is not None:
            lines = _insert_under_today(lines, today_idx, block)
        else:
            lines = _insert_new_section(lines, [today + "\n", "\n"] + block)

        write_lines(lines)
        git_snapshot(f"add: {title}")
    print(f"Entry added under {today}")


def cmd_edit(date_arg: str | None = None, title: str | None = None) -> None:
    """Open a subsection in $EDITOR; splice the result back into the devlog."""
    # Lock is held for the duration of the editor session so that a
    # concurrent write can't shift line numbers under us. Editor sessions
    # are interactive so other devlog writers will block — acceptable
    # for a solo-user tool.
    with write_lock():
        lines = read_lines()
        _, sub_start, sub_end = _resolve_target(lines, date_arg, title)

        editor = os.environ.get("EDITOR", "vim")
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".md", encoding="utf-8", delete=False
        ) as tf:
            tf.writelines(lines[sub_start:sub_end])
            tmp_path = tf.name

        try:
            subprocess.run([editor, tmp_path], check=True)
            with open(tmp_path, encoding="utf-8") as f:
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


def cmd_amend(
    new_text: str, date_arg: str | None = None, title: str | None = None
) -> None:
    """Replace the body of a subsection (keep the title line).

    The new body is always prefixed with a ``[HH:MM] AMENDED:`` marker
    line so the amend time is visible inline."""
    with write_lock():
        lines = read_lines()
        _, sub_start, sub_end = _resolve_target(lines, date_arg, title)
        title_line = lines[sub_start]
        now = datetime.now().strftime("%H:%M")
        body_lines = [f"[{now}] AMENDED:"] + new_text.strip().splitlines()
        new_body = ["\n"]
        for line in body_lines:
            new_body.append(line + "\n")
        new_body.append("\n")
        lines = lines[:sub_start] + [title_line] + new_body + lines[sub_end:]
        write_lines(lines)
        git_snapshot(f"amend: {_title_text(title_line)}")
    print(f"Amended: {title_line.rstrip()}")


def cmd_addend(
    new_text: str, date_arg: str | None = None, title: str | None = None
) -> None:
    """Append a paragraph to the bottom of a subsection's body.

    The first line of the appended paragraph is always prefixed with
    ``[HH:MM] ADDENDUM:`` so later additions read as deliberate temporal
    events."""
    with write_lock():
        lines = read_lines()
        _, sub_start, sub_end = _resolve_target(lines, date_arg, title)
        title_line = lines[sub_start]
        insert_pos = sub_end
        while insert_pos > sub_start + 1 and not lines[insert_pos - 1].strip():
            insert_pos -= 1
        body_lines = new_text.strip().splitlines()
        if body_lines:
            now = datetime.now().strftime("%H:%M")
            body_lines[0] = f"[{now}] ADDENDUM: {body_lines[0]}"
        addend = ["\n"]
        for line in body_lines:
            addend.append(line + "\n")
        addend.append("\n")
        lines = lines[:insert_pos] + addend + lines[insert_pos:]
        write_lines(lines)
        git_snapshot(f"addend: {_title_text(title_line)}")
    print(f"Added to: {title_line.rstrip()}")


def cmd_undo() -> None:
    """Revert the most recent commit in the data repo (`git revert HEAD`)."""
    repo = os.path.dirname(DEVLOG)
    if not os.path.isdir(os.path.join(repo, ".git")):
        sys.exit("No git repo at devlog data dir — nothing to undo")
    head_subj = subprocess.run(
        ["git", "-C", repo, "log", "-1", "--format=%s"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    with write_lock():
        subprocess.run(
            ["git", "-C", repo, "revert", "HEAD", "--no-edit"],
            check=True,
        )
    print(f"Undid: {head_subj}")


def cmd_retitle(date_arg: str, old_title: str, new_title: str) -> None:
    """Rename a subsection in place, preserving the [HH:MM] timestamp."""
    target = parse_date_arg(date_arg)
    target_heading = format_date_heading(target)
    with write_lock():
        lines = read_lines()
        outside = compute_outside_fence(lines)
        if not any(
            outside[i] and line.rstrip() == target_heading
            for i, line in enumerate(lines)
        ):
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


def cmd_rm(date_arg: str, title: str, dry_run: bool = False) -> None:
    """Delete a subsection (and the date section if it becomes empty)."""
    target = parse_date_arg(date_arg)
    target_heading = format_date_heading(target)

    if dry_run:
        return _rm_impl(target_heading, title, dry_run=True)
    with write_lock():
        return _rm_impl(target_heading, title, dry_run=False)


def _rm_impl(target_heading: str, title: str, dry_run: bool) -> None:
    """Body of cmd_rm — separated so it can run with or without write_lock."""
    lines = read_lines()

    outside = compute_outside_fence(lines)
    if not any(
        outside[i] and line.rstrip() == target_heading
        for i, line in enumerate(lines)
    ):
        sys.exit(f"No section for {target_heading}")

    found = find_subsection(lines, target_heading, title)
    if found is None:
        sys.exit(f"No subsection '{title}' under {target_heading}")
    date_idx, sub_start, sub_end = found
    section_end = find_section_end(lines, date_idx)

    new_lines = lines[:sub_start] + lines[sub_end:]
    new_section_end = section_end - (sub_end - sub_start)
    new_outside = compute_outside_fence(new_lines)
    has_sub = any(
        new_outside[i] and SUB_PAT.match(new_lines[i])
        for i in range(date_idx + 1, new_section_end)
    )
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
