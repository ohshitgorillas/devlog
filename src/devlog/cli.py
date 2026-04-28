"""Command-line interface: argparse subcommands dispatched to read/write helpers."""

import argparse
import os
import sys

from .migrate import migrate_if_needed
from .read import (
    cmd_date,
    cmd_diff,
    cmd_exists,
    cmd_find,
    cmd_last,
    cmd_list,
    cmd_log,
    cmd_recent,
)
from .store import capture_manual_edits
from .write import (
    cmd_addend,
    cmd_amend,
    cmd_edit,
    cmd_retitle,
    cmd_rm,
    cmd_undo,
    insert_entry,
)


def _resolve_body(arg):
    """`-` means read from stdin; otherwise return arg verbatim."""
    if arg == "-":
        return sys.stdin.read()
    return arg


def _add_write_subparsers(sub):
    """Attach the add/edit/amend/addend/retitle/rm subparsers to `sub`."""
    p_add = sub.add_parser("add", help="add new subsection under today")
    p_add.add_argument("-t", "--title", required=True)
    p_add.add_argument(
        "-e",
        "--entry",
        required=True,
        help="body text (use `-` to read from stdin)",
    )
    p_add.add_argument(
        "-n",
        "--name",
        default=os.environ.get("DEVLOG_NAME"),
        help="append author name to title (env: DEVLOG_NAME)",
    )

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

    p_retitle = sub.add_parser("retitle", help="rename existing subsection")
    p_retitle.add_argument("-d", "--date", required=True)
    p_retitle.add_argument("-t", "--title", required=True, help="current title")
    p_retitle.add_argument("--to", required=True, help="new title", dest="new_title")

    p_rm = sub.add_parser("rm", help="delete named subsection")
    p_rm.add_argument("-d", "--date", required=True)
    p_rm.add_argument("-t", "--title", required=True)
    p_rm.add_argument(
        "-n",
        "--dry-run",
        action="store_true",
        help="print what would be removed without writing",
    )


def _add_read_subparsers(sub):
    """Attach the show/find/recent/list/last/exists subparsers to `sub`."""
    p_show = sub.add_parser("show", help="print full day section")
    p_show.add_argument("date", metavar="DATE", help="YYYYMMDD or MMDD")
    p_show.add_argument("--json", action="store_true", dest="json_out")

    p_find = sub.add_parser("find", help="search subsections (case-insensitive)")
    p_find.add_argument("term")
    p_find.add_argument("--json", action="store_true", dest="json_out")

    p_recent = sub.add_parser("recent", help="last N days (default 7)")
    p_recent.add_argument("days", nargs="?", type=int, default=7)
    p_recent.add_argument("--json", action="store_true", dest="json_out")

    p_list = sub.add_parser("list", help="print dates + titles only (no bodies)")
    p_list.add_argument("--json", action="store_true", dest="json_out")

    p_last = sub.add_parser("last", help="print newest subsection")
    p_last.add_argument("--json", action="store_true", dest="json_out")

    p_exists = sub.add_parser(
        "exists",
        help="exit 0 if subsection exists, 1 otherwise (no output)",
    )
    p_exists.add_argument("-d", "--date", required=True)
    p_exists.add_argument("-t", "--title", required=True)


def _add_repo_subparsers(sub):
    """Attach the log/diff/undo subparsers (data-repo wrappers) to `sub`."""
    p_log = sub.add_parser("log", help="show data-repo commit history")
    p_log.add_argument(
        "n", nargs="?", type=int, default=20, help="number of commits (default 20)"
    )

    p_diff = sub.add_parser("diff", help="show data-repo commit diff")
    p_diff.add_argument("ref", nargs="?", default="HEAD", help="git ref (default HEAD)")

    sub.add_parser("undo", help="revert last commit in the data repo")


def build_parser():
    """Construct the argparse top-level parser with every subcommand attached."""
    parser = argparse.ArgumentParser(
        prog="devlog",
        description="Append/read/edit ~/devlog.md",
    )
    sub = parser.add_subparsers(dest="cmd", metavar="COMMAND")
    _add_write_subparsers(sub)
    _add_read_subparsers(sub)
    _add_repo_subparsers(sub)
    return parser


def main():
    """Run migration + manual-edit capture, then dispatch the requested subcommand."""
    migrate_if_needed()
    capture_manual_edits()
    parser = build_parser()
    args = parser.parse_args()

    if args.cmd is None:
        parser.print_help()
        return

    dispatch = {
        "add": lambda: insert_entry(
            f"{args.title} - {args.name}" if args.name else args.title,
            _resolve_body(args.entry),
        ),
        "show": lambda: cmd_date(args.date, args.json_out),
        "find": lambda: cmd_find(args.term, args.json_out),
        "recent": lambda: cmd_recent(args.days, args.json_out),
        "list": lambda: cmd_list(args.json_out),
        "last": lambda: cmd_last(args.json_out),
        "exists": lambda: cmd_exists(args.date, args.title),
        "edit": lambda: cmd_edit(args.date, args.title),
        "amend": lambda: cmd_amend(_resolve_body(args.body), args.date, args.title),
        "addend": lambda: cmd_addend(_resolve_body(args.body), args.date, args.title),
        "log": lambda: cmd_log(args.n),
        "diff": lambda: cmd_diff(args.ref),
        "undo": cmd_undo,
        "retitle": lambda: cmd_retitle(args.date, args.title, args.new_title),
        "rm": lambda: cmd_rm(args.date, args.title, args.dry_run),
    }
    dispatch[args.cmd]()


if __name__ == "__main__":
    main()
