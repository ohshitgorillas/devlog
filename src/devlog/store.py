import contextlib
import fcntl
import os
import re
import tempfile

DEVLOG = os.path.expanduser("~/devlog.md")
LOCKFILE = os.path.expanduser("~/.devlog.lock")
DATE_PAT = re.compile(r"^## [A-Z][a-z]+ \d{1,2}, \d{4}$")
SUB_PAT = re.compile(r"^### ")
TITLE_PAT = re.compile(r"^### (?:\[\d{2}:\d{2}\] )?(.*)$")


@contextlib.contextmanager
def write_lock():
    """Hold an exclusive flock for the duration of a read-modify-write op.
    Reads are not blocked (advisory lock; readers don't acquire it)."""
    fd = os.open(LOCKFILE, os.O_RDWR | os.O_CREAT, 0o600)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
        yield
    finally:
        fcntl.flock(fd, fcntl.LOCK_UN)
        os.close(fd)


def read_lines():
    with open(DEVLOG) as f:
        return f.readlines()


def write_lines(lines):
    """Atomic write: stage to a tempfile in the same directory, then
    rename over the target. POSIX rename is atomic, so a crash mid-write
    can never leave a truncated/corrupt devlog."""
    d = os.path.dirname(DEVLOG) or "."
    fd, tmp = tempfile.mkstemp(prefix=".devlog.", dir=d)
    try:
        with os.fdopen(fd, "w") as f:
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


def find_subsection(lines, target_heading, title):
    """Return (date_idx, sub_start, sub_end) for a subsection matching
    `title` under `target_heading` (e.g. '## April 27, 2026'), or None."""
    date_idx = next(
        (i for i, l in enumerate(lines) if l.rstrip() == target_heading), None
    )
    if date_idx is None:
        return None
    section_end = len(lines)
    for i in range(date_idx + 1, len(lines)):
        if DATE_PAT.match(lines[i].rstrip()):
            section_end = i
            break
    sub_start = None
    for i in range(date_idx + 1, section_end):
        m = TITLE_PAT.match(lines[i].rstrip())
        if m and m.group(1) == title:
            sub_start = i
            break
    if sub_start is None:
        return None
    sub_end = section_end
    for i in range(sub_start + 1, section_end):
        if SUB_PAT.match(lines[i]):
            sub_end = i
            break
    return (date_idx, sub_start, sub_end)


def find_last_subsection(lines):
    """Return (date_idx, sub_start, sub_end) of newest subsection, or None."""
    date_idx = next((i for i, l in enumerate(lines) if DATE_PAT.match(l.rstrip())), None)
    if date_idx is None:
        return None
    section_end = len(lines)
    for i in range(date_idx + 1, len(lines)):
        if DATE_PAT.match(lines[i].rstrip()):
            section_end = i
            break
    sub_start = None
    for i in range(date_idx + 1, section_end):
        if SUB_PAT.match(lines[i]):
            sub_start = i
            break
    if sub_start is None:
        return None
    sub_end = section_end
    for i in range(sub_start + 1, section_end):
        if SUB_PAT.match(lines[i]):
            sub_end = i
            break
    return (date_idx, sub_start, sub_end)
