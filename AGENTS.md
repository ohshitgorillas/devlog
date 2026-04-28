# devlog — AI agent instructions

Terse reference for AI assistants writing to `~/.devlog/devlog.md` via the `devlog` CLI. Never write the file directly. Reading direct = fine.

## When to log

- After any non-trivial change to system state, infra, config, code outside a git repo, or any change you'd want recoverable context for later.
- One subsection per logical change. Don't bundle unrelated edits.
- Skip: pure read ops, throwaway exploration, trivial typo fixes already captured in git.

## Add new entry

```sh
devlog add -t "Brief title" -e "What changed, which files, why if non-obvious."
```

- Title: imperative, ≤60 chars. No date prefix (tool adds `[HH:MM]`).
- Entry: factual + terse. What changed → files touched → why (only if non-obvious).
- Title collision under same date = error. Pick distinct title or use `amend`/`addend`.

Multi-line body:

```sh
devlog add -t "Title" -e $'line1\nline2\nline3'
# or
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

`amend`/`addend`/`edit` accept `-` for stdin body.

## Read

| Op | Command | JSON |
|----|---------|------|
| Day section | `devlog show YYYYMMDD` | `--json` |
| Day (MMDD) | `devlog show 0428` (most recent past) | `--json` |
| Search | `devlog find TERM` (case-insensitive substring) | `--json` |
| Last N days | `devlog recent [N]` (default 7) | `--json` |
| Index | `devlog list` (dates + titles, no bodies) | `--json` |
| Newest | `devlog last` | `--json` |
| Existence check | `devlog exists -d YYYYMMDD -t "Title"` (exit 0/1) | — |

Prefer `--json` when piping into another tool or parsing programmatically.

## Repo introspection

```sh
devlog log [N]      # commit history (default 20)
devlog diff [REF]   # git show REF (default HEAD)
```

## Style for entries

- Lead with what changed. Then files. Then why if non-obvious.
- Use backticks for paths, commands, identifiers.
- Match existing entries in the same log — check `devlog last` or `devlog recent 3` first.
- No marketing voice. No "successfully". No restating the title.
- Don't log the act of logging.

## Hard rules

- Never `echo >> ~/devlog.md`, `sed -i`, or otherwise touch the file directly. Direct edits are captured on next CLI run, but you lose the structured commit message.
- Never invent dates. Today's date is set by the tool.
- Never delete entries to "clean up" unless explicitly told. Use `amend` to correct content; use `rm` only when an entry is wrong/duplicate and the user has authorized removal.
- `undo` reverts only the most recent commit. For older fixes, use `git -C ~/.devlog revert <sha>`.
- `amend` and `addend` refuse past-date targets. Use `devlog edit -d YYYYMMDD -t "Title"` to modify older entries (no auto-timestamp).

## Failure modes

- "Subsection 'X' already exists under ..." → title collision. Pick distinct title or use `addend` to extend the existing one.
- "No subsection 'X' under ..." → wrong title or wrong date. Run `devlog list` or `devlog show <date>` to find correct title.
- "No entries" → empty log; `add` first.
- "No entry for ..." (`show`) → that date has no section.

## Env

- `DEVLOG_FILE` — override data path.
- `DEVLOG_NAME` — author suffix appended to titles (`### [HH:MM] Title - name`). Or pass `-n NAME` per `add`.
- `EDITOR` — used by `devlog edit`.
