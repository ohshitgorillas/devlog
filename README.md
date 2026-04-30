# tephra

A small CLI for keeping a topic-organized development log as a directory of Markdown files. Each topic is its own file (`Topic.md`), with entries organized as `## YYYY-MM-DD (HH:MM) — Title` headings sorted newest-first. Every CLI write auto-commits to a private git repo in the vault directory, so nothing is lost and bad writes can be reverted.

The format is hand-editable in any text editor and renders cleanly in [Obsidian](https://obsidian.md/), where wikilinks (`[[Topic#anchor]]`) double as cross-references between entries.

## Why tephra

I keep a log to track homelab changes. `git` doesn't fit (`/` would be an absurd repo) and the changes I care about span multiple systems anyway. Any significant configuration changes, package installations, etc. were recorded in `~/devlog.md`.

Enter Claude Code: agents work faster than I can, but getting them to log their actions consistently was insanely frustrating. Despite explicit instructions in `CLAUDE.md`, agents would freestyle the format, create duplicate date headers or simply enter the wrong date, append instead of prepend, etc. It took no less than five frustrated prompts per session to keep the devlog consistent.

Getting information out of the log for agents was its own hurdle: `grep` doesn't work when entires span multiple lines, so your choices are to either copy-paste by hand or dump the whole file and burn context on noise.

`tephra` fixes both ends. Agents and humans alike get a simple CLI for maintaining and referencing the document.

## What tephra provides

- A clean, simple CLI for adding entries to logs.
- Optional `**Related:**` line per entry holding `[[Topic#anchor]]` wikilinks to specific cross-topic entries. Cross-link targets are validated on insert.
- Atomic writes (tempfile + `os.replace`), so a crash mid-write cannot leave a file corrupt.
- A file lock around every write, so concurrent `tephra` invocations on the same host serialize cleanly instead of clobbering each other.
- A private git repo at the vault root that auto-commits every CLI write. Direct edits to topic files (with Obsidian, `vim`, `sed`, an editor plugin, whatever) are detected on the next CLI invocation and committed as `manual edit (captured)`, so nothing slips past the history.
- Read commands (`show`, `find`, `recent`, `list`, `last`, `exists`) with optional `--json` output, suitable for piping into other tools or AI agents. Cross-topic by default; `-T TOPIC` filters.
- Edit commands (`amend`, `addend`, `retitle`, `rm`) that target the newest entry in a topic by default, or any entry via `--date` + `--title`.
- An `undo` command that wraps `git revert HEAD` on the data repo, so even a bad write is recoverable without reaching into git directly.

## What tephra doesn't provide

Encryption. Bring your own, or avoid entering sensitive data.

## Install

A regular Python package. From a clone of this repo:

```sh
python -m venv ~/.local/share/tephra-venv
~/.local/share/tephra-venv/bin/pip install -e .
ln -s ~/.local/share/tephra-venv/bin/tephra ~/.local/bin/tephra
```

Editable install: changes to the source take effect immediately.

## Usage

Create a topic (only way to add topics — `add` will refuse unknown topics):

```sh
tephra topic add Notes
tephra topic list
```

Add a new entry under a topic:

```sh
tephra add -T Notes -t "Brief title" -e "What changed, files touched, why."
```

Cross-link to other entries with `--related` (repeatable, validated):

```sh
tephra add -T O11y -t "Title" -e "body" \
  --related "Bittorrent#2026-04-24 — peer port metric"
```

Read commands (cross-topic by default; pass `-T TOPIC` to restrict):

```sh
tephra show 2026-04-28          # entries on a date
tephra show 0428                # MMDD: most recent past 04-28
tephra find "wireguard"         # case-insensitive substring search
tephra find "wg" --days 7       # ... restricted to the last 7 days
tephra find "wg" --since 2026-04-01   # ... or to entries on/after a date
tephra recent 7                 # last 7 calendar days (default 7)
tephra list                     # headings only, no bodies
tephra last                     # newest entry
tephra exists -T Notes -d 2026-04-28 -t "Title"   # exit 0 if exists, 1 otherwise
```

Edit commands (default to newest entry in the topic; pass `-d` + `-t` to target a specific one):

```sh
tephra amend -T TOPIC "new body"            # replace body; preserves Related line
tephra amend -T TOPIC "new body" --related "Topic#anchor"   # rewrite Related
tephra amend -T TOPIC "new body" --no-related               # drop Related
tephra addend -T TOPIC "extra para"         # append paragraph above any Related line
tephra addend -T TOPIC "" --related "Topic#anchor"          # extend Related only (deduped)
tephra retitle -T TOPIC -d 2026-04-28 -t "Old" --to "New"
tephra rm -T TOPIC -d 2026-04-28 -t "Title"
tephra rm -T TOPIC -d 2026-04-28 -t "Title" -n              # dry-run preview
```

`-d DATE` accepts `YYYY-MM-DD`, `YYYYMMDD`, or `MMDD`. There is no `edit` subcommand — open the topic file in your editor of choice (Obsidian GUI, vim, etc.); direct edits are auto-captured to git on the next CLI invocation.

Repo commands:

```sh
tephra log [N]                  # last N commits (default 20)
tephra diff [REF]               # git show REF (default HEAD)
tephra undo                     # revert last commit in data repo
tephra manual-commit "MSG"      # commit pending manual edits with custom message
```

Multi-line bodies from a shell are easiest with `$'...\n...'` quoting, or by passing `-` as the body and piping in stdin:

```sh
tephra add -T TOPIC -t "Title" -e $'first line\nsecond line'
some-command | tephra add -T TOPIC -t "Title" -e -
tephra amend -T TOPIC - < new_body.txt
```

`--json` output is available on `show`, `find`, `recent`, `list`, and `last`.

## Configuration

The vault path is stored in `$XDG_CONFIG_HOME/tephra/vault` (typically `~/.config/tephra/vault`):

```sh
tephra config vault /path/to/your/vault   # set
tephra config show                        # inspect resolved path
```

Default if unset: `$XDG_DATA_HOME/tephra/vault` (typically `~/.local/share/tephra/vault`).

## Data layout

```
<vault>/
├── Topic1.md          # one file per topic, H1 + H2 entries
├── Topic2.md
├── ...
├── .git/              # auto-commit history
└── .tephra.lock       # advisory write lock
```

Each topic file looks like:

```markdown
# Topic1

## 2026-04-28 (14:32) — newer entry

Body.

**Related:** [[Topic2#2026-04-27 — earlier entry]]

## 2026-04-27 (09:15) — older entry

Body.
```

Each CLI write produces one commit with a message like `add: [Topic] TITLE`, `amend: [Topic] TITLE`, `rm: [Topic] TITLE`. Direct edits are committed as `manual edit (captured)` on the next invocation, or with a custom message via `tephra manual-commit "MSG"` before the next CLI write.

## Obsidian integration

The vault is a normal directory of markdown files — point Obsidian at it and entries render with working wikilinks (`[[Topic#anchor]]`). The `.obsidian/` directory Obsidian creates inside the vault is independent of `tephra`; you may want to gitignore `.obsidian/workspace.json` to avoid noisy auto-commits of UI state.

## Recovery

The git repo at the vault root is the source of truth for history. If a write went wrong:

```sh
tephra undo                            # revert most recent commit
tephra log                             # commit history
tephra diff <ref>                      # inspect a past version
git -C "$(tephra config path)" revert <ref>   # selectively undo any past commit
```

## For AI agents

See [`skills/tephra/SKILL.md`](skills/tephra/SKILL.md) for an AI-optimized reference covering when to log, command tables, style guidance, and failure modes. The file is a Claude Code skill (loaded by Claude Code's skill discovery via the YAML frontmatter) but is human-readable as a regular markdown reference.

## License

MIT — see [`LICENSE`](LICENSE).
