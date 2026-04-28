import os
import re

DEVLOG = os.path.expanduser("~/devlog.md")
DATE_PAT = re.compile(r"^## [A-Z][a-z]+ \d{1,2}, \d{4}$")
SUB_PAT = re.compile(r"^### ")
TITLE_PAT = re.compile(r"^### (?:\[\d{2}:\d{2}\] )?(.*)$")


def read_lines():
    with open(DEVLOG) as f:
        return f.readlines()


def write_lines(lines):
    with open(DEVLOG, "w") as f:
        f.writelines(lines)


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
