"""Date helpers: parse user-supplied dates and format markdown headings.

Month names are formatted and parsed via an explicit English list rather
than ``strftime``/``strptime`` ``%B``, which is locale-sensitive. This
keeps the data file format stable regardless of ``LC_TIME``.
"""

from __future__ import annotations

import re
import sys
from datetime import datetime

MONTHS = [
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
]

_HEADING_PAT = re.compile(r"^([A-Za-z]+) (\d{1,2}), (\d{4})$")


def format_date_heading(dt: datetime) -> str:
    """Return ``dt`` formatted as a level-2 markdown heading line."""
    return f"## {MONTHS[dt.month - 1]} {dt.day}, {dt.year}"


def today_heading() -> str:
    """Return today's date as a markdown heading line, e.g. '## April 28, 2026'."""
    return format_date_heading(datetime.now())


def parse_date_heading(line: str) -> datetime | None:
    """Parse a date heading into a datetime, or None."""
    stripped = line.strip().lstrip("# ").rstrip()
    m = _HEADING_PAT.match(stripped)
    if not m:
        return None
    month_name, day_s, year_s = m.group(1), m.group(2), m.group(3)
    if month_name not in MONTHS:
        return None
    try:
        return datetime(int(year_s), MONTHS.index(month_name) + 1, int(day_s))
    except ValueError:
        return None


def parse_date_arg(arg: str) -> datetime:
    """Parse YYYYMMDD or MMDD into a datetime. MMDD resolves to the most
    recent past occurrence (devlog entries are always past): if the date
    in the current year is in the future, fall back to the prior year."""
    arg = arg.strip()
    if len(arg) == 8:
        return datetime.strptime(arg, "%Y%m%d")
    if len(arg) == 4:
        now = datetime.now()
        candidate = datetime.strptime(f"{now.year}{arg}", "%Y%m%d")
        if candidate.date() > now.date():
            candidate = candidate.replace(year=now.year - 1)
        return candidate
    sys.exit(f"Invalid date format '{arg}' — use YYYYMMDD or MMDD")
