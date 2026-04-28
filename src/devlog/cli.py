import argparse
import sys

from .read import cmd_date, cmd_exists, cmd_find, cmd_last, cmd_list, cmd_recent
from .write import cmd_addend, cmd_amend, cmd_edit, cmd_rm, insert_entry


def _resolve_body(arg):
    """`-` means read from stdin; otherwise return arg verbatim."""
    if arg == "-":
        return sys.stdin.read()
    return arg


def build_parser():
    parser = argparse.ArgumentParser(
        prog="devlog",
        description="Append/read/edit ~/devlog.md",
    )
    sub = parser.add_subparsers(dest="cmd", metavar="COMMAND")

    p_add = sub.add_parser("add", help="add new subsection under today")
    p_add.add_argument("-t", "--title", required=True)
    p_add.add_argument(
        "-e", "--entry", required=True,
        help="body text (use `-` to read from stdin)",
    )

    p_show = sub.add_parser("show", help="print full day section")
    p_show.add_argument("date", metavar="DATE", help="YYYYMMDD or MMDD")

    p_find = sub.add_parser("find", help="search subsections (case-insensitive)")
    p_find.add_argument("term")

    p_recent = sub.add_parser("recent", help="last N days (default 7)")
    p_recent.add_argument("days", nargs="?", type=int, default=7)

    sub.add_parser("list", help="print dates + titles only (no bodies)")

    sub.add_parser("last", help="print newest subsection")

    p_exists = sub.add_parser(
        "exists",
        help="exit 0 if subsection exists, 1 otherwise (no output)",
    )
    p_exists.add_argument("-d", "--date", required=True)
    p_exists.add_argument("-t", "--title", required=True)

    p_edit = sub.add_parser(
        "edit", help="open subsection in $EDITOR (newest by default)"
    )
    p_edit.add_argument("-d", "--date", help="target a specific subsection")
    p_edit.add_argument("-t", "--title", help="target a specific subsection")

    p_amend = sub.add_parser(
        "amend", help="replace body of subsection (newest by default)"
    )
    p_amend.add_argument("body", help="new body (use `-` to read from stdin)")
    p_amend.add_argument("-d", "--date", help="target a specific subsection")
    p_amend.add_argument("-t", "--title", help="target a specific subsection")

    p_addend = sub.add_parser(
        "addend", help="append paragraph to subsection (newest by default)"
    )
    p_addend.add_argument("body", help="paragraph (use `-` to read from stdin)")
    p_addend.add_argument("-d", "--date", help="target a specific subsection")
    p_addend.add_argument("-t", "--title", help="target a specific subsection")

    p_rm = sub.add_parser("rm", help="delete named subsection")
    p_rm.add_argument("-d", "--date", required=True)
    p_rm.add_argument("-t", "--title", required=True)
    p_rm.add_argument(
        "-n", "--dry-run", action="store_true",
        help="print what would be removed without writing",
    )

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()

    if args.cmd is None:
        parser.print_help()
        return

    dispatch = {
        "add": lambda: insert_entry(args.title, _resolve_body(args.entry)),
        "show": lambda: cmd_date(args.date),
        "find": lambda: cmd_find(args.term),
        "recent": lambda: cmd_recent(args.days),
        "list": cmd_list,
        "last": cmd_last,
        "exists": lambda: cmd_exists(args.date, args.title),
        "edit": lambda: cmd_edit(args.date, args.title),
        "amend": lambda: cmd_amend(_resolve_body(args.body), args.date, args.title),
        "addend": lambda: cmd_addend(_resolve_body(args.body), args.date, args.title),
        "rm": lambda: cmd_rm(args.date, args.title, args.dry_run),
    }
    dispatch[args.cmd]()


if __name__ == "__main__":
    main()
