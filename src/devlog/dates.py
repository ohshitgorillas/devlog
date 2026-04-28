from __future__ import annotations

import sys
from datetime import datetime


def today_heading() -> str:
    return datetime.now().strftime("## %B %-d, %Y")


def parse_date_heading(line: str) -> datetime | None:
    """Parse a date heading into a datetime, or None."""
    try:
        return datetime.strptime(line.strip().lstrip("# "), "%B %d, %Y")
    except ValueError:
        try:
            return datetime.strptime(line.strip().lstrip("# "), "%B %-d, %Y")
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
