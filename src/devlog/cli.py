import argparse

from .read import cmd_date, cmd_find, cmd_recent
from .write import cmd_addend, cmd_amend, cmd_edit_last, cmd_rm, insert_entry


def build_parser():
    parser = argparse.ArgumentParser(
        prog="devlog",
        description="Append/read/edit ~/devlog.md",
    )
    sub = parser.add_subparsers(dest="cmd", metavar="COMMAND")

    p_add = sub.add_parser("add", help="add new subsection under today")
    p_add.add_argument("-t", "--title", required=True)
    p_add.add_argument("-e", "--entry", required=True, help="body text")

    p_show = sub.add_parser("show", help="print full day section")
    p_show.add_argument("date", metavar="DATE", help="YYYYMMDD or MMDD")

    p_find = sub.add_parser("find", help="search subsections (case-insensitive)")
    p_find.add_argument("term")

    p_recent = sub.add_parser("recent", help="last N days (default 7)")
    p_recent.add_argument("days", nargs="?", type=int, default=7)

    sub.add_parser("edit", help="open newest subsection in $EDITOR")

    p_amend = sub.add_parser("amend", help="replace body of newest subsection")
    p_amend.add_argument("body")

    p_addend = sub.add_parser("addend", help="append paragraph to bottom of newest subsection")
    p_addend.add_argument("body")

    p_rm = sub.add_parser("rm", help="delete named subsection")
    p_rm.add_argument("-d", "--date", required=True)
    p_rm.add_argument("-t", "--title", required=True)

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()

    if args.cmd is None:
        parser.print_help()
        return

    dispatch = {
        "add": lambda: insert_entry(args.title, args.entry),
        "show": lambda: cmd_date(args.date),
        "find": lambda: cmd_find(args.term),
        "recent": lambda: cmd_recent(args.days),
        "edit": cmd_edit_last,
        "amend": lambda: cmd_amend(args.body),
        "addend": lambda: cmd_addend(args.body),
        "rm": lambda: cmd_rm(args.date, args.title),
    }
    dispatch[args.cmd]()


if __name__ == "__main__":
    main()
