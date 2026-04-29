---
name: devlog
description: >
  Append, read, and edit a dated development log at ~/.devlog/devlog.md via the
  `devlog` CLI. Use when user says "log this", "add to devlog", "/devlog",
  "what did I do on <date>", "find <term> in the log", or after any
  non-trivial change to system state, infra, config, or code outside a git
  repo. Never edit ~/.devlog/devlog.md directly — the CLI handles atomic
  writes, locking, and per-write git auto-commits.
---

Tool for keeping a dated and timestamped development log. One file (`~/.devlog/devlog.md`), `## Date` headings with `### [HH:MM] Title` subsections. Every CLI write auto-commits to a private git repo at `~/.devlog/`. Direct edits captured on next CLI invocation.

## When and what to log

**NOTE TO USER**: edit this section to your preferred scope. Agents: if this line remains, confirm scope before logging.

- After any non-trivial change to system state, infra, config, or code.
- One subsection per logical change. Don't bundle unrelated edits.
- Skip: pure read ops, throwaway exploration, trivial fixes already captured in git, the act of logging

## How to log

- User will supply the scope of the log.
- Be terse, concise, and precise
- Lead with what changed. Then files. Then why if non-obvious.
- Backticks for paths, commands, identifiers.
- Match existing entries in the same log — check `devlog last` or `devlog recent 3` first.
- No marketing voice. No "successfully". No restating the title.

## Add new entry

```sh
devlog add -t "Brief title" -e "What changed, which files, why if non-obvious."
```

- Title: imperative, ≤60 chars. No date prefix (tool adds `[HH:MM]`).
- Entry: factual + terse. What changed → files touched → why (only if non-obvious).
- Title collision under same date = error. Pick distinct title or use `amend` / `addend`.

Multi-line body:

```sh
devlog add -t "Title" -e $'line1\nline2\nline3'
some-cmd | devlog add -t "Title" -e -
```

## Edit / extend / fix

Default target = newest subsection. Pass `-d YYYYMMDD -t "Title"` to target a specific one.

| Op | Command |
|----|---------|
| Append paragraph (today only) | `devlog addend "more context"` — auto-prefixed `[HH:MM] ADDENDUM:` |
| Replace body, keep title (today only) | `devlog amend "new body"` — auto-prefixed `[HH:MM] AMENDED:` |
| Open in $EDITOR | `devlog edit` |
| Rename | `devlog retitle -d 20260428 -t "Old" --to "New"` |
| Delete | `devlog rm -d 20260428 -t "Title"` |
| Preview delete | `devlog rm -d 20260428 -t "Title" -n` |
| Revert last commit | `devlog undo` |

`amend` / `addend` / `edit` accept `-` for stdin body.

## Read

| Op | Command | JSON |
|----|---------|------|
| Day section | `devlog show YYYYMMDD` | `--json` |
| Day (MMDD) | `devlog show 0428` (most recent past) | `--json` |
| Search | `devlog find TERM` (case-insensitive substring) | `--json` |
| Last N days | `devlog recent [N]` (default 7) | `--json` |
| Index | `devlog list` (dates + titles, no bodies) | `--json` |
| Newest | `devlog last` | `--json` |
| Existence | `devlog exists -d YYYYMMDD -t "Title"` (exit 0/1) | — |

Prefer `--json` when piping into another tool or parsing programmatically.

## Repo introspection

```sh
devlog log [N]      # commit history (default 20)
devlog diff [REF]   # git show REF (default HEAD)
```

## Hard rules

- Never `echo >> ~/devlog.md`, `sed -i`, or otherwise touch the file directly. Direct edits get captured on next CLI run, but you lose the structured commit message.
- Never invent dates. Tool sets today.
- Never delete entries to "clean up" unless explicitly told. Use `amend` to correct content; use `rm` only when an entry is wrong/duplicate and the user has authorized removal.
- `undo` reverts only the most recent commit. For older fixes: `git -C ~/.devlog revert <sha>`.
- `amend` and `addend` only operate on today's entries. Modifying a past-date entry through them would stamp it with the current `[HH:MM]`, which would imply that time happened on the past date. Use `devlog edit -d YYYYMMDD -t "Title"` to modify past entries (no auto-timestamp).
- Always check for relevant entries under the current date (`devlog --recent 1` or `devlog find TERM`) to amend/append before creating a new section. Always prefer `addend` over adding new entries.

## Failure modes

- `Subsection 'X' already exists under ...` → title collision. Pick distinct title or use `addend` to extend the existing one.
- `No subsection 'X' under ...` → wrong title or wrong date. Run `devlog list` or `devlog show <date>` to find correct title.
- `No entries` → empty log; `add` first.
- `No entry for ...` (`show`) → that date has no section.

## Env

- `DEVLOG_FILE` — override data path.
- `DEVLOG_NAME` — author suffix appended to titles (`### [HH:MM] Title - name`). Or pass `-n NAME` per `add`.
- `EDITOR` — used by `devlog edit`.
