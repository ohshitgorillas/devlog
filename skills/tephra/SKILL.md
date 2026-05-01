---
name: tephra
description: >
  Append, read, and amend a topic-based markdown journal in an Obsidian-style
  vault via the `tephra` CLI. Use when user says "log this", "add to tephra",
  "/tephra", "what did I do on <date>", "find <term> in the log", or after any
  non-trivial change to system state, infra, config, or code outside a git
  repo. Never edit topic files directly — the CLI handles atomic writes,
  locking, and per-write git auto-commits.
---

Tool for keeping a topic-organized development journal as Obsidian-style markdown. Each topic is a single file (`Topic.md`); files may live in the vault root or in a folder (`<vault>/<Folder>/<Topic>.md`). Entries are H2 sections (`## YYYY-MM-DD (HH:MM) — Title`) sorted newest-first. Every CLI write auto-commits to the vault git repo. Direct edits in the Obsidian GUI are auto-captured to git on next CLI invocation.

## When and what to log

- After any non-trivial change to system state, infra, config, or code.
- One entry per topic, per day per change. Group related changes; don't bundle unrelated ones.
- Skip: pure read ops, throwaway exploration, trivial fixes already captured in git, the act of logging.
- **CRITICAL**: Contents are stored in plain text. DO NOT ENTER SENSITIVE INFORMATION.

## How to log

- Be terse, concise, accurate.
- Lead with what changed. Then files. Then why if non-obvious.
- Backticks for paths, commands, identifiers. HTML-tag-looking tokens (`<name>`, `<HOST>`) are auto-backticked on insert.
- Match existing entries in the same topic — check `tephra last -T TOPIC` or `tephra recent 3 -T TOPIC` first.
- No marketing voice. No "successfully". No restating the title.
- Always cross-link related prior entries with `--related`. Before writing a new entry, run `tephra find TERM` for the subsystem(s) the change touches and `tephra recent 14 -T <other-topics>` for adjacent topics. Pass each relevant prior entry as `--related "Topic#YYYY-MM-DD [(HH:MM)] — Title"`. The flag is repeatable. Cross-links are how the journal stays navigable as it grows; an unlinked entry is invisible to future searches that start from a related entry. Default to over-linking when in doubt — the validator will reject anything that doesn't exist.

### When to add a related link

Link to any prior entry that:

- introduced the thing this entry modifies, fixes, or extends ("introduced", "added", "first deployed");
- documented a bug or symptom that this entry fixes;
- documented a related decision, alert, or threshold this entry tunes;
- spans the same incident, refactor, or migration across multiple sessions;
- touches an adjacent subsystem the reader might want to jump to (e.g. an `O11y` alert change linking to the `Bittorrent` exporter that emits the metric).

If you can't find anything to link after a quick `tephra find`, that's a valid outcome — but explicitly searched > silently skipped. The default assumption should be "this almost certainly relates to *something* prior; find it."

## Add new entry

```sh
tephra add -T TOPIC -t "Brief title" -e "What changed, which files, why if non-obvious."
```

- `-T` is required and must be a known topic (see `tephra topic list`).
- Bare `-T Topic` resolves to the configured default folder (see `tephra config show`). Override with `-T Folder:Topic`.
- For read commands only (`show`, `find`, `recent`, `list`, `last`): `-T Folder:` (trailing colon, no topic) scopes to all topics in `Folder`. Write/existence commands reject this form.
- Title: imperative, ≤60 chars.
- Entry: factual + terse. What changed → files touched → why (only if non-obvious).
- Title collision on same date in same topic = error. Pick distinct title or use `amend`/`addend`.

Multi-line body:

```sh
tephra add -T TOPIC -t "Title" -e $'line1\nline2'
some-cmd | tephra add -T TOPIC -t "Title" -e -
```

`-e` is repeatable — each value becomes a separate paragraph (joined with a blank line, in CLI order):

```sh
tephra add -T TOPIC -t "Title" \
  -e "First paragraph." \
  -e "Second paragraph."
```

At most one `-e` may be `-` (stdin is read once). Empty `-e ""` slots are dropped (so `addend -e "" --related ...` still extends the Related line without adding a paragraph). Same `-e` flag and join semantics apply on `amend` and `addend`.

Cross-link to other entries with `--related`:

```sh
tephra add -T O11y -t "Title" -e "body" \
  --related "Bittorrent#2026-04-24 — peer port metric"
```

`--related` is repeatable. Anchor format: `Topic#YYYY-MM-DD [(HH:MM)] — Title`. Refs are validated against the target topic file (exact match required).

## Topic management

```sh
tephra topic list [-F FOLDER]   # known topics (default folder unless -F)
tephra topic add NAME [-F FOLDER]
tephra folder list              # vault subdirectories
```

Topics cannot be added implicitly via `add` — the topic file must already exist.

## Edit / extend / fix

Default target = newest entry in the topic. Pass `-d YYYY-MM-DD -t "Title"` (or `-d YYYYMMDD` / `-d MMDD`) to target a specific one.

| Op | Command |
|----|---------|
| Append paragraph | `tephra addend -T TOPIC -e "more context"` |
| Append paragraph + extend Related line | `tephra addend -T TOPIC -e "..." --related "Topic#anchor"` |
| Replace body, keep heading + Related | `tephra amend -T TOPIC -e "new body"` |
| Replace body + rewrite Related | `tephra amend -T TOPIC -e "..." --related "Topic#anchor"` |
| Replace body + drop Related | `tephra amend -T TOPIC -e "..." --no-related` |
| Rename | `tephra retitle -T TOPIC -d 2026-04-28 -t "Old" --to "New"` |
| Delete | `tephra rm -T TOPIC -d 2026-04-28 -t "Title"` |
| Preview delete | `tephra rm -T TOPIC -d 2026-04-28 -t "Title" -n` |
| Revert last commit | `tephra undo` |

`amend` / `addend` use the same repeatable `-e`/`--entry` as `add`. Pass `-e -` to read body from stdin.

## Read

Cross-topic by default. Pass `-T TOPIC` to restrict to one topic, or `-T Folder:` to restrict to all topics in a folder.

| Op | Command | JSON |
|----|---------|------|
| Entries on a date | `tephra show YYYY-MM-DD` | `--json` |
| Date (MMDD) | `tephra show 0428` (most recent past) | `--json` |
| Search | `tephra find TERM` (case-insensitive; `--days N` or `--since DATE` to limit window) | `--json` |
| Last N days | `tephra recent [N]` (default 7) | `--json` |
| Index | `tephra list` (headings only) | `--json` |
| Newest | `tephra last` | `--json` |
| Existence | `tephra exists -T TOPIC -d DATE -t "Title"` (exit 0/1) | — |

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
tephra log [N]      # commit history (default 20)
tephra diff [REF]   # git show REF (default HEAD)
```

## Hard rules

- Never `echo >>` to a topic file, `sed -i`, or otherwise touch files directly. Direct edits get captured on next CLI run, but you lose the structured commit message.
- Never invent dates. Tool sets today.
- Never delete entries to "clean up" unless explicitly told. Use `amend` to correct content; use `rm` only when an entry is wrong/duplicate and the user has authorized removal.
- `undo` reverts only the most recent commit. For older fixes: `git -C "$(tephra config path)" revert <sha>` against the vault repo.
- Before `add`: search today with `tephra recent 1` or `tephra find TERM --days 1`. If a same-day same-topic entry already covers this change, `addend` to it instead of creating a new one.
- Before `add` (separate pass, looking further back): `tephra find` for the subsystem and adjacent topics. Pass every relevant prior entry as `--related`. Skipping this step orphans the entry from the rest of the journal.
- Never include sensitive information.

## Failure modes

- `Entry 'X' already exists on YYYY-MM-DD in topic '...'` → title collision. Pick distinct title or `addend` to extend the existing one.
- `No entry 'X' on YYYY-MM-DD in topic '...'` → wrong title, date, or topic. Run `tephra list -T TOPIC` to find correct title.
- `Unknown topic '...'. Known: ...` → typo or missing topic. Run `tephra topic list`; create with `tephra topic add NAME` if needed.
- `Related ref: no entry '...'` → cross-link target doesn't exist. Verify with `tephra find` or `tephra list -T TOPIC`.
- `No entries` → empty topic; `add` first.

## Vault location

The vault path is stored in `$XDG_CONFIG_HOME/tephra/vault` (typically `~/.config/tephra/vault`). Set with `tephra config vault PATH`; inspect with `tephra config show`. Default if unset: `$XDG_DATA_HOME/tephra/vault` (typically `~/.local/share/tephra/vault`).

The default folder for `-T Topic` is stored at `$XDG_CONFIG_HOME/tephra/default_folder`. Set with `tephra config default-folder NAME`; clear with empty string (writes go to vault root).

## Auto-sync

Optional. When enabled and the vault repo has an `origin` remote, every CLI write op runs `git pull --rebase --autostash` before the local commit and `git push` after.

```sh
tephra config auto-sync on        # enable
tephra config auto-sync off       # disable
```

- **Pull conflict:** the write is aborted and the repo is left mid-rebase. Subsequent tephra writes refuse to run until you finish the rebase manually:
  ```sh
  git -C "$(tephra config path)" status
  git -C "$(tephra config path)" rebase --continue   # or --abort
  ```
- **Network failure on pull:** warns to stderr, continues with the local commit. Offline use keeps working; the next successful sync reconciles.
- **Push failure:** warns to stderr; the local commit is preserved. The next write op's pre-pull + push will reconcile.
- **No `origin` remote / auto-sync off:** behaves identically to no-sync mode (no-op).

Optional Prometheus textfile metric:

```sh
tephra config sync-metric /var/lib/node_exporter/textfile_collector/tephra_sync.prom
tephra config sync-metric ""       # disable
```

Emits `tephra_sync_status` (1 clean, 0 conflict/push failure) and `tephra_sync_last_attempt` (Unix timestamp), atomically (tmp + rename) on every sync attempt.
