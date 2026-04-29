"""Date helpers: parse user-supplied dates as ISO YYYY-MM-DD strings."""

from __future__ import annotations

import re
import sys
from datetime import datetime

ISO_PAT = re.compile(r"^(\d{4})-(\d{2})-(\d{2})$")


def today_iso() -> str:
    """Return today's date in ISO format (YYYY-MM-DD)."""
    return datetime.now().strftime("%Y-%m-%d")


def now_time() -> str:
    """Return current time as HH:MM."""
    return datetime.now().strftime("%H:%M")


def parse_date_arg(arg: str) -> str:
    """Parse YYYYMMDD, YYYY-MM-DD, or MMDD into an ISO YYYY-MM-DD string.

    MMDD resolves to the most recent past occurrence: if the date in the
    current year is in the future, fall back to the prior year.
    """
    arg = arg.strip()
    if ISO_PAT.match(arg):
        try:
            datetime.strptime(arg, "%Y-%m-%d")
        except ValueError:
            sys.exit(f"Invalid date '{arg}'")
        return arg
    if len(arg) == 8 and arg.isdigit():
        try:
            return datetime.strptime(arg, "%Y%m%d").strftime("%Y-%m-%d")
        except ValueError:
            sys.exit(f"Invalid date '{arg}'")
    if len(arg) == 4 and arg.isdigit():
        now = datetime.now()
        try:
            candidate = datetime.strptime(f"{now.year}{arg}", "%Y%m%d")
        except ValueError:
            sys.exit(f"Invalid date '{arg}'")
        if candidate.date() > now.date():
            candidate = candidate.replace(year=now.year - 1)
        return candidate.strftime("%Y-%m-%d")
    sys.exit(f"Invalid date format '{arg}' — use YYYY-MM-DD, YYYYMMDD, or MMDD")
