# devlog

A small CLI for keeping a dated development log in a single Markdown file at `~/.devlog/devlog.md`. Entries are organized as `## Date` headings with `### [HH:MM] Title` subsections under each. Every CLI write auto-commits to a private git repo in the same directory, so nothing is lost and bad writes can be reverted.

## Why it exists

This tool started as a workaround for a recurring frustration with AI coding assistants: when asked to record what they just did in a `CHANGELOG.md` or development log, they could not consistently decide whether to put the new entry at the top or the bottom of the file. Some assistants would prepend, some would append, some would do both in the same session, and the resulting file would drift into a confused mess of newest-first and oldest-first sections that no human or model could later parse reliably.

`devlog` removes that decision. New subsections always go under today's date heading, and today's date heading always sits at the top of the file. Newest-first ordering is enforced by the tool, not by the writer's discretion.

It is also intended for cases where a development log is genuinely useful but git is the wrong fit. The original use case here was tracking system-wide changes on a homelab server, where edits live in `/etc`, in `/srv`, in systemd units, in firewall rules, in container compose files scattered across the filesystem. Committing `/` to a single repo is absurd, but the work still benefits from a written record. `devlog` gives you one without forcing the underlying changes into version control.

The same shape applies anywhere you want a durable, searchable log that isn't tied to a specific repo: dotfile tweaks, ops actions on a production host, household IT chores, research notes, anything where "what did I change last Tuesday and why" is a question you'd like to be able to answer six months later.

## What it gives you

- A single Markdown file at `~/.devlog/devlog.md`, organized as `## Date` headings with `### [HH:MM] Title` subsections.
- Atomic writes (tempfile + `os.replace`), so a crash mid-write cannot leave the file corrupt.
- A file lock around every write, so concurrent `devlog` invocations on the same host serialize cleanly instead of clobbering each other.
- A private git repo at `~/.devlog/` that auto-commits every CLI write. Direct edits to the file (with `vim`, `sed`, an editor plugin, whatever) are detected on the next CLI invocation and committed as `manual edit (captured)`, so nothing slips past the history.
- Read commands (`show`, `find`, `recent`, `list`, `last`, `exists`) with optional `--json` output, suitable for piping into other tools or AI agents.
- Edit commands (`edit`, `amend`, `addend`, `retitle`, `rm`) that target the newest subsection by default, or any subsection via `--date` + `--title`.
- An `undo` command that wraps `git revert HEAD` on the data repo, so even a bad write is recoverable without reaching into git directly.

## Install

A regular Python package. From a clone of this repo:

```sh
python -m venv ~/.local/share/devlog-venv
~/.local/share/devlog-venv/bin/pip install -e .
ln -s ~/.local/share/devlog-venv/bin/devlog ~/.local/bin/devlog
```

Editable install: changes to the source take effect immediately.

## Usage

Add a new subsection under today's date:

```sh
devlog add -t "Brief title" -e "What changed, files touched, why."
```

Read commands:

```sh
devlog show 20260428          # full day section
devlog show 0428              # MMDD: most recent past 04-28
devlog find "wireguard"       # case-insensitive substring search
devlog recent 7               # last 7 calendar days (default 7)
devlog list                   # dates + titles only, no bodies
devlog last                   # newest subsection
devlog exists -d 20260428 -t "Title"   # exit 0 if exists, 1 otherwise
```

Edit commands (default to newest subsection; pass `-d` + `-t` to target a specific one):

```sh
devlog edit                   # open in $EDITOR (fallback: vim)
devlog amend "new body"       # replace body, prefixed "[HH:MM] AMENDED:"
devlog addend "extra para"    # append paragraph, prefixed "[HH:MM] ADDENDUM:"
devlog retitle -d 20260428 -t "Old" --to "New"
devlog rm -d 20260428 -t "Title"
devlog rm -d 20260428 -t "Title" -n      # dry-run preview
```

`amend` and `addend` only work on today's entries — they stamp the body with the current `[HH:MM]`, which would be wrong on a past-date section. Use `devlog edit -d YYYYMMDD -t "Title"` to modify older entries (no auto-timestamp).

Repo commands:

```sh
devlog log [N]                # last N commits (default 20)
devlog diff [REF]             # git show REF (default HEAD)
devlog undo                   # revert last commit in data repo
```

Multi-line bodies from a shell are easiest with `$'...\n...'` quoting, or by passing `-` as the body and piping in stdin:

```sh
devlog add -t "Title" -e $'first line\nsecond line'
some-command | devlog add -t "Title" -e -
devlog amend - < new_body.txt
```

`--json` output is available on `show`, `find`, `recent`, `list`, and `last`.

## Configuration

- `DEVLOG_FILE` — override the data file path. Disables the legacy-migration step.
- `DEVLOG_NAME` — author name appended to titles when set, e.g. `### [HH:MM] Title - alice`. Can be passed per-invocation with `devlog add -n NAME`.
- `EDITOR` — used by `devlog edit`. Defaults to `vim`.

## Data layout

```
~/.devlog/
├── devlog.md          # the actual log
├── .git/              # auto-commit history
└── .devlog.lock       # advisory write lock
~/devlog.md            # back-compat symlink (created on migration)
```

Each CLI write produces one commit with a message like `add: TITLE`, `amend: TITLE`, `rm: TITLE`. Direct edits to `devlog.md` are committed as `manual edit (captured)` on the next invocation.

## Recovery

The git repo at `~/.devlog/` is the source of truth for history. If a write went wrong:

```sh
devlog undo                    # revert most recent commit
devlog log                     # commit history
devlog diff <ref>              # inspect a past version
git -C ~/.devlog revert <ref>  # selectively undo any past commit
```

## For AI agents

See [`AGENTS.md`](AGENTS.md) for a terse, AI-optimized reference covering when to log, command tables, style guidance, and failure modes.

## Migration from the legacy script

If you previously used the original single-file `~/devlog.md` shell script, the first invocation of the packaged CLI moves the data to `~/.devlog/devlog.md`, leaves a back-compat symlink at `~/devlog.md`, and seeds a git repo with an `import existing devlog` baseline commit. The migration is idempotent and is a no-op once the new path exists or `DEVLOG_FILE` is set.
