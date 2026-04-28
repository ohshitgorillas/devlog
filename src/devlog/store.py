"""Filesystem and git operations on the devlog data file."""

import contextlib
import fcntl
import os
import re
import subprocess
import sys
import tempfile

DEVLOG = os.environ.get("DEVLOG_FILE") or os.path.expanduser("~/.devlog/devlog.md")
LOCKFILE = os.path.join(os.path.dirname(DEVLOG), ".devlog.lock")
DATE_PAT = re.compile(r"^## [A-Z][a-z]+ \d{1,2}, \d{4}$")
SUB_PAT = re.compile(r"^### ")
TITLE_PAT = re.compile(r"^### (?:\[\d{2}:\d{2}\] )?(.*)$")
TITLE_TS_PAT = re.compile(r"^### (?:\[(\d{2}:\d{2})\] )?(.*)$")


def parse_title_line(line):
    """Split a '### [HH:MM] Title' line into (ts, title). ts is None
    if no timestamp prefix is present."""
    m = TITLE_TS_PAT.match(line.rstrip())
    if m:
        return m.group(1), m.group(2)
    return None, line.rstrip()


@contextlib.contextmanager
def write_lock():
    """Hold an exclusive flock for the duration of a read-modify-write op.
    Reads are not blocked (advisory lock; readers don't acquire it)."""
    os.makedirs(os.path.dirname(LOCKFILE), exist_ok=True)
    fd = os.open(LOCKFILE, os.O_RDWR | os.O_CREAT, 0o600)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
        yield
    finally:
        fcntl.flock(fd, fcntl.LOCK_UN)
        os.close(fd)


def read_lines():
    """Return the devlog file contents as a list of lines (with newlines)."""
    with open(DEVLOG, encoding="utf-8") as f:
        return f.readlines()


def _git(repo, *args, check=True):
    return subprocess.run(
        ["git", "-C", repo, *args],
        check=check,
        capture_output=True,
        text=True,
    )


def init_repo(repo):
    """Init a git repo at `repo` if absent, and ensure a usable identity
    (local config only, never touching global)."""
    if os.path.isdir(os.path.join(repo, ".git")):
        return
    _git(repo, "init", "-q", "-b", "main")
    if not _git(repo, "config", "user.email", check=False).stdout.strip():
        _git(repo, "config", "user.email", "devlog@localhost")
        _git(repo, "config", "user.name", "devlog")


def capture_manual_edits():
    """If the data file has uncommitted diffs vs HEAD, commit them as a
    'manual edit' so direct edits (vim, sed, scp) are still captured in
    git history. No-op if no repo or no diffs."""
    repo = os.path.dirname(DEVLOG)
    if not os.path.isdir(os.path.join(repo, ".git")):
        return
    fname = os.path.basename(DEVLOG)
    try:
        diff = _git(repo, "diff", "--quiet", "HEAD", "--", fname, check=False)
        if diff.returncode == 0:
            return
        _git(repo, "add", fname)
        _git(repo, "commit", "-q", "-m", "manual edit (captured)")
        print(
            f"note: captured manual edit to {DEVLOG}",
            file=sys.stderr,
        )
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        print(f"warning: capture_manual_edits failed: {e}", file=sys.stderr)


def git_snapshot(message):
    """Stage everything and commit. Best-effort: a failure here doesn't
    abort the surrounding write op (the data is already saved). No-op if
    nothing changed."""
    repo = os.path.dirname(DEVLOG)
    try:
        init_repo(repo)
        _git(repo, "add", "-A")
        diff = _git(repo, "diff", "--cached", "--quiet", check=False)
        if diff.returncode != 0:
            _git(repo, "commit", "-q", "-m", message)
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        print(f"warning: git snapshot failed: {e}", file=sys.stderr)


def write_lines(lines):
    """Atomic write: stage to a tempfile in the same directory, then
    rename over the target. POSIX rename is atomic, so a crash mid-write
    can never leave a truncated/corrupt devlog."""
    d = os.path.dirname(DEVLOG) or "."
    os.makedirs(d, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".devlog.", dir=d)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.writelines(lines)
        os.replace(tmp, DEVLOG)
    except Exception:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def parse_sections(lines):
    """Return list of (date_heading_line, [content_lines]) for each date section."""
    sections = []
    current_heading = None
    current_lines = []
    for line in lines:
        if DATE_PAT.match(line.rstrip()):
            if current_heading is not None:
                sections.append((current_heading, current_lines))
            current_heading = line.rstrip()
            current_lines = []
        elif current_heading is not None:
            current_lines.append(line)
    if current_heading is not None:
        sections.append((current_heading, current_lines))
    return sections


def parse_subsections(content_lines):
    """Split section content into list of (title_line, [body_lines])."""
    subs = []
    current_title = None
    current_body = []
    for line in content_lines:
        if SUB_PAT.match(line):
            if current_title is not None:
                subs.append((current_title, current_body))
            current_title = line.rstrip()
            current_body = []
        elif current_title is not None:
            current_body.append(line)
    if current_title is not None:
        subs.append((current_title, current_body))
    return subs


def find_section_end(lines, date_idx):
    """Return the index of the next date heading after `date_idx`, or len(lines)."""
    for i in range(date_idx + 1, len(lines)):
        if DATE_PAT.match(lines[i].rstrip()):
            return i
    return len(lines)


def _find_sub_start(lines, lo, hi, matches):
    """Return the first index in [lo, hi) whose subsection title satisfies `matches`."""
    for i in range(lo, hi):
        if matches(lines[i]):
            return i
    return None


def _find_sub_end(lines, sub_start, section_end):
    """Return the start index of the next subsection after `sub_start`, capped at section_end."""
    for i in range(sub_start + 1, section_end):
        if SUB_PAT.match(lines[i]):
            return i
    return section_end


def _title_matches(title):
    """Return a predicate matching a '### [HH:MM] Title' line whose title equals `title`."""

    def predicate(line):
        m = TITLE_PAT.match(line.rstrip())
        return bool(m) and m.group(1) == title

    return predicate


def find_subsection(lines, target_heading, title):
    """Return (date_idx, sub_start, sub_end) for a subsection matching
    `title` under `target_heading` (e.g. '## April 27, 2026'), or None."""
    date_idx = next(
        (i for i, line in enumerate(lines) if line.rstrip() == target_heading), None
    )
    if date_idx is None:
        return None
    section_end = find_section_end(lines, date_idx)
    sub_start = _find_sub_start(lines, date_idx + 1, section_end, _title_matches(title))
    if sub_start is None:
        return None
    sub_end = _find_sub_end(lines, sub_start, section_end)
    return (date_idx, sub_start, sub_end)


def find_last_subsection(lines):
    """Return (date_idx, sub_start, sub_end) of newest subsection, or None."""
    date_idx = next(
        (i for i, line in enumerate(lines) if DATE_PAT.match(line.rstrip())), None
    )
    if date_idx is None:
        return None
    section_end = find_section_end(lines, date_idx)
    sub_start = _find_sub_start(
        lines, date_idx + 1, section_end, lambda line: bool(SUB_PAT.match(line))
    )
    if sub_start is None:
        return None
    sub_end = _find_sub_end(lines, sub_start, section_end)
    return (date_idx, sub_start, sub_end)
