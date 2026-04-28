import sys
from datetime import datetime


def today_heading():
    return datetime.now().strftime("## %B %-d, %Y")


def parse_date_heading(line):
    """Parse a date heading into a datetime, or None."""
    try:
        return datetime.strptime(line.strip().lstrip("# "), "%B %d, %Y")
    except ValueError:
        try:
            return datetime.strptime(line.strip().lstrip("# "), "%B %-d, %Y")
        except ValueError:
            return None


def parse_date_arg(arg):
    """Parse YYYYMMDD or MMDD into a datetime."""
    arg = arg.strip()
    if len(arg) == 8:
        return datetime.strptime(arg, "%Y%m%d")
    elif len(arg) == 4:
        return datetime.strptime(f"{datetime.now().year}{arg}", "%Y%m%d")
    else:
        sys.exit(f"Invalid date format '{arg}' — use YYYYMMDD or MMDD")
