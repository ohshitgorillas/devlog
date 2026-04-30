"""Command-line interface: argparse subcommands dispatched to read/write helpers."""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timedelta

from . import __version__
from .dates import parse_date_arg
from .read import (
    cmd_diff,
    cmd_exists,
    cmd_find,
    cmd_last,
    cmd_list,
    cmd_log,
    cmd_recent,
    cmd_show,
)
from .store import capture_manual_edits, cmd_manual_commit
from .topics import (
    cmd_config_default_folder,
    cmd_config_path,
    cmd_config_show,
    cmd_config_vault,
    cmd_folder_list,
    cmd_topic_add,
    cmd_topic_list,
    parse_topic_arg,
)
from .write import (
    cmd_addend,
    cmd_amend,
    cmd_retitle,
    cmd_rm,
    cmd_undo,
    insert_entry,
)


def _resolve_body(arg: str) -> str:
    """``-`` reads from stdin; otherwise return ``arg`` verbatim."""
    if arg == "-":
        return sys.stdin.read()
    return arg


def _parse_topic(arg: str | None) -> tuple[str | None, str | None]:
    """Parse a ``-T`` value into ``(folder, topic)``. ``None`` arg → both None."""
    if arg is None:
        return None, None
    return parse_topic_arg(arg)


def _add_write_subparsers(sub: argparse._SubParsersAction) -> None:
    p_add = sub.add_parser("add", help="add new entry to a topic")
    p_add.add_argument("-T", "--topic", required=True)
    p_add.add_argument("-t", "--title", required=True)
    p_add.add_argument(
        "-e", "--entry", required=True, help="body text (use `-` to read stdin)"
    )
    p_add.add_argument(
        "--related",
        action="append",
        default=[],
        metavar="REF",
        help="cross-link: 'Topic#YYYY-MM-DD [(HH:MM)] — Title' (repeatable)",
    )

    p_amend = sub.add_parser(
        "amend", help="replace body of entry (newest in topic by default)"
    )
    p_amend.add_argument("-T", "--topic", required=True)
    p_amend.add_argument("body", help="new body (use `-` to read stdin)")
    p_amend.add_argument("-d", "--date")
    p_amend.add_argument("-t", "--title")
    p_amend.add_argument(
        "--related",
        action="append",
        default=[],
        metavar="REF",
        help="rewrite Related line with these refs (repeatable)",
    )
    p_amend.add_argument(
        "--no-related", action="store_true", help="drop existing Related line"
    )

    p_addend = sub.add_parser(
        "addend", help="append paragraph to entry (newest in topic by default)"
    )
    p_addend.add_argument("-T", "--topic", required=True)
    p_addend.add_argument("body", help="paragraph (use `-` to read stdin)")
    p_addend.add_argument("-d", "--date")
    p_addend.add_argument("-t", "--title")
    p_addend.add_argument(
        "--related",
        action="append",
        default=[],
        metavar="REF",
        help="append refs to Related line, deduped (repeatable)",
    )

    p_retitle = sub.add_parser("retitle", help="rename existing entry")
    p_retitle.add_argument("-T", "--topic", required=True)
    p_retitle.add_argument("-d", "--date", required=True)
    p_retitle.add_argument("-t", "--title", required=True, help="current title")
    p_retitle.add_argument("--to", required=True, help="new title", dest="new_title")

    p_rm = sub.add_parser("rm", help="delete entry from a topic")
    p_rm.add_argument("-T", "--topic", required=True)
    p_rm.add_argument("-d", "--date", required=True)
    p_rm.add_argument("-t", "--title", required=True)
    p_rm.add_argument(
        "-n",
        "--dry-run",
        action="store_true",
        help="print what would be removed without writing",
    )


def _add_read_subparsers(sub: argparse._SubParsersAction) -> None:
    p_show = sub.add_parser("show", help="print entries on a date")
    p_show.add_argument("date", metavar="DATE", help="YYYY-MM-DD, YYYYMMDD, or MMDD")
    p_show.add_argument("-T", "--topic", help="restrict to a single topic")
    p_show.add_argument("--json", action="store_true", dest="json_out")

    p_find = sub.add_parser("find", help="search entries (case-insensitive)")
    p_find.add_argument("term")
    p_find.add_argument("-T", "--topic")
    p_find.add_argument("--json", action="store_true", dest="json_out")
    g_find = p_find.add_mutually_exclusive_group()
    g_find.add_argument(
        "--days",
        type=int,
        metavar="N",
        help="restrict to entries within the last N days",
    )
    g_find.add_argument(
        "--since", metavar="DATE", help="restrict to entries on or after DATE"
    )

    p_recent = sub.add_parser("recent", help="entries from the last N days (default 7)")
    p_recent.add_argument("days", nargs="?", type=int, default=7)
    p_recent.add_argument("-T", "--topic")
    p_recent.add_argument("--json", action="store_true", dest="json_out")

    p_list = sub.add_parser("list", help="print all entry headings (no bodies)")
    p_list.add_argument("-T", "--topic")
    p_list.add_argument("--json", action="store_true", dest="json_out")

    p_last = sub.add_parser("last", help="print newest entry")
    p_last.add_argument("-T", "--topic")
    p_last.add_argument("--json", action="store_true", dest="json_out")

    p_exists = sub.add_parser(
        "exists", help="exit 0 if entry exists, 1 otherwise (no output)"
    )
    p_exists.add_argument("-T", "--topic", required=True)
    p_exists.add_argument("-d", "--date", required=True)
    p_exists.add_argument("-t", "--title", required=True)


def _add_topic_subparsers(sub: argparse._SubParsersAction) -> None:
    p_topic = sub.add_parser("topic", help="topic management")
    topic_sub = p_topic.add_subparsers(dest="topic_cmd", metavar="SUBCOMMAND")
    p_tlist = topic_sub.add_parser("list", help="print known topics")
    p_tlist.add_argument(
        "-F", "--folder", help="folder to list (default: configured default folder)"
    )
    p_tadd = topic_sub.add_parser("add", help="create a new topic file")
    p_tadd.add_argument("name")
    p_tadd.add_argument(
        "-F", "--folder", help="folder to create in (default: configured default folder)"
    )


def _add_folder_subparsers(sub: argparse._SubParsersAction) -> None:
    p_folder = sub.add_parser("folder", help="folder management")
    folder_sub = p_folder.add_subparsers(dest="folder_cmd", metavar="SUBCOMMAND")
    folder_sub.add_parser("list", help="print folder names (vault subdirectories)")


def _add_config_subparsers(sub: argparse._SubParsersAction) -> None:
    p_config = sub.add_parser("config", help="vault location configuration")
    config_sub = p_config.add_subparsers(dest="config_cmd", metavar="SUBCOMMAND")
    p_vault = config_sub.add_parser("vault", help="set the vault path")
    p_vault.add_argument("path", help="vault directory")
    p_default_folder = config_sub.add_parser(
        "default-folder",
        help="set or clear the default folder (use empty string to clear)",
    )
    p_default_folder.add_argument(
        "folder", help="folder name (empty string clears default → vault root)"
    )
    config_sub.add_parser("show", help="print resolved vault path + source")
    config_sub.add_parser(
        "path", help="print resolved vault path only (for shell scripting)"
    )


def _add_repo_subparsers(sub: argparse._SubParsersAction) -> None:
    p_log = sub.add_parser("log", help="show vault repo commit history")
    p_log.add_argument("n", nargs="?", type=int, default=20)

    p_diff = sub.add_parser("diff", help="show vault repo commit diff")
    p_diff.add_argument("ref", nargs="?", default="HEAD")

    sub.add_parser("undo", help="revert last commit in the vault repo")

    p_manual = sub.add_parser(
        "manual-commit",
        help="commit pending vault edits with a custom message",
    )
    p_manual.add_argument("message", help="commit message")


def build_parser() -> argparse.ArgumentParser:
    """Construct the argparse top-level parser with every subcommand attached."""
    parser = argparse.ArgumentParser(
        prog="tephra",
        description="Topic-based markdown journal CLI for Obsidian-style vaults.",
    )
    parser.add_argument(
        "--version", action="version", version=f"%(prog)s {__version__}"
    )
    sub = parser.add_subparsers(dest="cmd", metavar="COMMAND")
    _add_write_subparsers(sub)
    _add_read_subparsers(sub)
    _add_topic_subparsers(sub)
    _add_folder_subparsers(sub)
    _add_config_subparsers(sub)
    _add_repo_subparsers(sub)
    return parser


def _resolve_find_since(args: argparse.Namespace) -> str | None:
    """Translate ``--days`` / ``--since`` on ``find`` into an ISO date cutoff."""
    if getattr(args, "days", None) is not None:
        return (datetime.now() - timedelta(days=args.days)).strftime("%Y-%m-%d")
    if getattr(args, "since", None) is not None:
        return parse_date_arg(args.since)
    return None


def _dispatch_topic(args: argparse.Namespace, parser: argparse.ArgumentParser) -> None:
    if args.topic_cmd == "list":
        cmd_topic_list(args.folder)
    elif args.topic_cmd == "add":
        cmd_topic_add(args.name, args.folder)
    else:
        parser.parse_args([args.cmd, "--help"])


def _dispatch_folder(args: argparse.Namespace, parser: argparse.ArgumentParser) -> None:
    if args.folder_cmd == "list":
        cmd_folder_list()
    else:
        parser.parse_args([args.cmd, "--help"])


def _dispatch_config(args: argparse.Namespace, parser: argparse.ArgumentParser) -> None:
    if args.config_cmd == "vault":
        cmd_config_vault(args.path)
    elif args.config_cmd == "default-folder":
        cmd_config_default_folder(args.folder or None)
    elif args.config_cmd == "show":
        cmd_config_show()
    elif args.config_cmd == "path":
        cmd_config_path()
    else:
        parser.parse_args([args.cmd, "--help"])


def main() -> None:
    """Capture manual vault edits, then dispatch the requested subcommand."""
    parser = build_parser()
    args = parser.parse_args()
    if args.cmd != "manual-commit":
        capture_manual_edits()

    if args.cmd is None:
        parser.print_help()
        return

    if args.cmd == "topic":
        _dispatch_topic(args, parser)
        return

    if args.cmd == "folder":
        _dispatch_folder(args, parser)
        return

    if args.cmd == "config":
        _dispatch_config(args, parser)
        return

    folder, topic = _parse_topic(getattr(args, "topic", None))

    dispatch = {
        "add": lambda: insert_entry(
            folder, topic, args.title, _resolve_body(args.entry), args.related or None
        ),
        "amend": lambda: cmd_amend(
            folder,
            topic,
            _resolve_body(args.body),
            args.date,
            args.title,
            args.related or None,
            args.no_related,
        ),
        "addend": lambda: cmd_addend(
            folder,
            topic,
            _resolve_body(args.body),
            args.date,
            args.title,
            args.related or None,
        ),
        "retitle": lambda: cmd_retitle(
            folder, topic, args.date, args.title, args.new_title
        ),
        "rm": lambda: cmd_rm(folder, topic, args.date, args.title, args.dry_run),
        "show": lambda: cmd_show(args.date, folder, topic, args.json_out),
        "find": lambda: cmd_find(
            args.term, folder, topic, args.json_out, _resolve_find_since(args)
        ),
        "recent": lambda: cmd_recent(args.days, folder, topic, args.json_out),
        "list": lambda: cmd_list(folder, topic, args.json_out),
        "last": lambda: cmd_last(folder, topic, args.json_out),
        "exists": lambda: cmd_exists(folder, topic, args.date, args.title),
        "log": lambda: cmd_log(args.n),
        "diff": lambda: cmd_diff(args.ref),
        "undo": cmd_undo,
        "manual-commit": lambda: cmd_manual_commit(args.message),
    }
    dispatch[args.cmd]()


if __name__ == "__main__":
    main()
