import os
import sys

from .read import cmd_date, cmd_find, cmd_recent
from .store import DEVLOG
from .write import cmd_addend, cmd_amend, cmd_edit_last, cmd_rm, insert_entry

HELP = """devlog — append/read/edit ~/devlog.md

Usage:
  devlog                              open in $EDITOR (vim)
  devlog --title T --entry BODY       add new subsection under today
  devlog --amend BODY                 replace body of newest subsection
  devlog --addend BODY                append paragraph to bottom of newest subsection
  devlog --edit-last                  open newest subsection in $EDITOR
  devlog --rm --date YYYYMMDD --title T   delete named subsection

Read:
  devlog --date YYYYMMDD | MMDD       full day section
  devlog --find TERM                  matching subsections (case-insensitive)
  devlog --recent [N]                 last N days (default 7)

Flags:
  -t/--title  -e/--entry  -d/--date  -f/--find  -r/--recent
  --edit-last  --amend  --addend  --rm  -h/--help
"""


def cmd_help():
    print(HELP, end="")


def main():
    args = sys.argv[1:]

    if not args:
        os.execvp("vim", ["vim", DEVLOG])
        return

    title = body = date_arg = amend_text = addend_text = None
    edit_last = rm_flag = False
    i = 0
    while i < len(args):
        a = args[i]
        if a in ("--help", "-h"):
            cmd_help()
            return
        elif a in ("--title", "-t") and i + 1 < len(args):
            title = args[i + 1]
            i += 2
        elif a in ("--entry", "-e") and i + 1 < len(args):
            body = args[i + 1]
            i += 2
        elif a in ("--date", "-d") and i + 1 < len(args):
            date_arg = args[i + 1]
            i += 2
        elif a in ("--find", "-f") and i + 1 < len(args):
            cmd_find(args[i + 1])
            return
        elif a in ("--recent", "-r"):
            n = 7
            if i + 1 < len(args) and args[i + 1].isdigit():
                n = int(args[i + 1])
                i += 2
            else:
                i += 1
            cmd_recent(n)
            return
        elif a == "--edit-last":
            edit_last = True
            i += 1
        elif a == "--amend" and i + 1 < len(args):
            amend_text = args[i + 1]
            i += 2
        elif a == "--addend" and i + 1 < len(args):
            addend_text = args[i + 1]
            i += 2
        elif a == "--rm":
            rm_flag = True
            i += 1
        else:
            sys.exit(f"Unknown argument: {a}")

    if edit_last:
        cmd_edit_last()
        return
    if amend_text is not None:
        cmd_amend(amend_text)
        return
    if addend_text is not None:
        cmd_addend(addend_text)
        return
    if rm_flag:
        if not date_arg or not title:
            sys.exit("--rm requires --date and --title")
        cmd_rm(date_arg, title)
        return
    if date_arg:
        cmd_date(date_arg)
        return
    if not title and not body:
        sys.exit("Usage: devlog [--title TITLE] [--entry TEXT]")

    insert_entry(title, body)


if __name__ == "__main__":
    main()
