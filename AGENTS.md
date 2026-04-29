# tephra — AI agent instructions

Terse reference for AI assistants writing to a tephra vault via the `tephra` CLI. Never write topic files directly. Reading direct = fine.

## When to log

- After any non-trivial change to system state, infra, config, code outside a git repo, or any change you'd want recoverable context for later.
- One entry per topic, per day per change. Group related changes; don't bundle unrelated ones.
- Before `add`: search today with `tephra recent 1` or `tephra find TERM --days 1`. If a related entry exists, `addend` to it. Otherwise `add`.
- Skip: pure read ops, throwaway exploration, trivial typo fixes already captured in git.

## Add new entry

```sh
tephra add -T TOPIC -t "Brief title" -e "What changed, which files, why if non-obvious."
```

- `-T TOPIC` is required. Topic must already exist (see `tephra topic list`); create with `tephra topic add NAME` if needed.
- Title: imperative, ≤60 chars.
- Entry: factual + terse. What changed → files touched → why (only if non-obvious).
- Title collision on same date in same topic = error. Pick distinct title or use `amend`/`addend`.

Multi-line body:

```sh
tephra add -T TOPIC -t "Title" -e $'line1\nline2\nline3'
# or
some-cmd | tephra add -T TOPIC -t "Title" -e -
```

Cross-link with `--related` (repeatable, validated):

```sh
tephra add -T O11y -t "Title" -e "body" \
  --related "Bittorrent#2026-04-24 — peer port metric" \
  --related "Network#2026-04-22 (14:31) — wg topology"
```

Anchor format: `Topic#YYYY-MM-DD [(HH:MM)] — Title`.

## Edit / extend / fix

Default target = newest entry in the topic. Pass `-d DATE -t "Title"` to target a specific one (`-d` accepts `YYYY-MM-DD`, `YYYYMMDD`, or `MMDD`).

| Op | Command |
|----|---------|
| Append paragraph | `tephra addend -T TOPIC "more context"` |
| Append + extend Related | `tephra addend -T TOPIC "..." --related "Topic#anchor"` |
| Replace body, keep heading + Related | `tephra amend -T TOPIC "new body"` |
| Replace body + rewrite Related | `tephra amend -T TOPIC "..." --related "Topic#anchor"` |
| Replace body + drop Related | `tephra amend -T TOPIC "..." --no-related` |
| Rename | `tephra retitle -T TOPIC -d 2026-04-28 -t "Old" --to "New"` |
| Delete | `tephra rm -T TOPIC -d 2026-04-28 -t "Title"` |
| Preview delete | `tephra rm -T TOPIC -d 2026-04-28 -t "Title" -n` |
| Revert last commit | `tephra undo` |

`amend`/`addend` accept `-` for stdin body.

## Read

Cross-topic by default. Pass `-T TOPIC` to restrict.

| Op | Command | JSON |
|----|---------|------|
| Entries on a date | `tephra show YYYY-MM-DD` | `--json` |
| Date (MMDD) | `tephra show 0428` (most recent past) | `--json` |
| Search | `tephra find TERM` (case-insensitive substring; `--days N` or `--since DATE` to limit window) | `--json` |
| Last N days | `tephra recent [N]` (default 7) | `--json` |
| Index | `tephra list` (headings only) | `--json` |
| Newest | `tephra last` | `--json` |
| Existence check | `tephra exists -T TOPIC -d DATE -t "Title"` (exit 0/1) | — |

Prefer `--json` when piping into another tool or parsing programmatically.

## When to read

Reach for the log to answer questions about prior work. Map prompt shape to command:

| Prompt shape | Command |
|--------------|---------|
| "changes to wireguard over the last 2 weeks" | `tephra find "wireguard" --days 14 --json` |
| "nginx broke overnight" | `tephra find "nginx" --days 2` |
| "summarize yesterday's work" | `tephra show YYYY-MM-DD` (yesterday's date) |
| "what did I last do to X?" | `tephra find "X"` then take newest match |
| "see the most recent entry" | `tephra last` |
| "summarize all project changes since April 1" | `tephra find "project" --since 2026-04-01` |
| "did I ever fix Z?" | `tephra find "Z"` |

Use `--json` when feeding output back into reasoning — the structured `{topic, date, time, title, body, related}` shape is easier to summarize than raw markdown.

## Repo introspection

```sh
tephra log [N]      # commit history of vault repo (default 20)
tephra diff [REF]   # git show REF (default HEAD)
```

## Style for entries

- Lead with what changed. Then files. Then why if non-obvious.
- Use backticks for paths, commands, identifiers. HTML-tag-looking tokens (`<name>`, `<HOST>`) are auto-backticked on insert.
- Match existing entries in the same topic — check `tephra last -T TOPIC` or `tephra recent 3 -T TOPIC` first.
- No marketing voice. No "successfully". No restating the title.
- Don't log the act of logging.

## Hard rules

- Never `echo >>` to a topic file, `sed -i`, or otherwise touch files directly. Direct edits are captured on next CLI run, but you lose the structured commit message.
- Never invent dates. Today's date is set by the tool.
- Never delete entries to "clean up" unless explicitly told. Use `amend` to correct content; use `rm` only when an entry is wrong/duplicate and the user has authorized removal.
- `undo` reverts only the most recent commit. For older fixes, run `git -C "$(tephra config path)" revert <sha>` against the vault repo.

## Failure modes

- "Entry 'X' already exists on YYYY-MM-DD in topic '...'" → title collision. Pick distinct title or `addend` to extend the existing one.
- "No entry 'X' on YYYY-MM-DD in topic '...'" → wrong title, date, or topic. Run `tephra list -T TOPIC` to find correct title.
- "Unknown topic '...'. Known: ..." → typo or missing topic. Run `tephra topic list`; create with `tephra topic add NAME` if needed.
- "Related ref: no entry '...'" → cross-link target doesn't exist. Verify with `tephra find` or `tephra list -T TOPIC`.
- "No entries" → empty topic / vault; `add` first.

## Vault location

The vault path is stored in `$XDG_CONFIG_HOME/tephra/vault` (typically `~/.config/tephra/vault`). Set with `tephra config vault PATH`; inspect with `tephra config show`. Default if unset: `$XDG_DATA_HOME/tephra/vault` (typically `~/.local/share/tephra/vault`).
