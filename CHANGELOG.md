# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.3.0] - 2026-04-29

### Added

- Folder-scoped reads: `-T Folder:` (trailing colon, empty topic) on `show`, `find`, `recent`, `list`, and `last` scopes the command to all topics in `Folder` instead of the configured default folder. `-T Folder:Topic` and bare `-T Topic` continue to work as before.

### Fixed

- `_resolve_scope` previously hardcoded the default folder when no topic was given, ignoring an explicit folder. Read commands now honor an explicit folder from `-T Folder:`.

### Changed

- Write/existence commands (`add`, `amend`, `addend`, `retitle`, `rm`, `exists`) reject `-T Folder:` (folder-only) with a clear error; a topic is required for those.

## [2.2.0] - 2026-04-29

### Added

- Folder-scoped vault layout: topic files may live in subdirectories (`<vault>/<Folder>/<Topic>.md`) in addition to the vault root.
- `-T Folder:Topic` syntax on all read/write commands to target a topic in a specific folder. Bare `-T Topic` uses the configured default folder.
- `tephra config default-folder NAME` to persist a default folder; pass an empty string to clear (writes to vault root). Stored at `$XDG_CONFIG_HOME/tephra/default_folder`.
- `tephra folder list` to enumerate folders (vault subdirectories).
- `tephra topic add NAME -F FOLDER` and `tephra topic list -F FOLDER` to scope topic management to a folder.
- `Folder:Topic#anchor` syntax in `--related` refs for cross-folder wikilinks.
- Read-command output labels now show `[Folder:Topic]` when the entry is folder-scoped.

### Changed

- `tephra config show` now also reports the configured default folder.

## [2.1.0] - 2026-04-29

### Added

- `tephra manual-commit "MSG"`: commit pending manual vault edits with a custom message instead of the default `manual edit (captured)`. Exits 1 with `nothing to commit` if the vault is clean.

## [2.0.0] - 2026-04-28

Renamed from `devlog` to `tephra`. Restructured from single-file (`~/.devlog/devlog.md`) to a topic-organized vault (one Markdown file per topic, format compatible with Obsidian).

### Added

- Topic-based vault layout: each topic is its own file (`Topic.md`) inside the vault directory.
- `tephra topic list` and `tephra topic add NAME` for topic management. Topics cannot be created implicitly via `add`.
- `tephra config vault PATH`, `tephra config show`, and `tephra config path` for vault-location management. Vault path persisted at `$XDG_CONFIG_HOME/tephra/vault`; default `$XDG_DATA_HOME/tephra/vault`.
- `--related "Topic#YYYY-MM-DD [(HH:MM)] — Title"` flag on `add`/`amend`/`addend` to author validated `[[Topic#anchor]]` wikilinks. Refs are resolved against the target topic file at invocation time; invalid refs error before any write. Repeatable.
- `--no-related` flag on `amend` to drop the Related line.
- `addend --related` appends to the existing Related line, deduped.
- Auto-backticking of HTML-tag-looking tokens (e.g. `<name>` → `` `<name>` ``) in entry bodies, skipping content inside fenced code blocks.
- Cross-topic read commands by default. `show`, `find`, `recent`, `list`, `last` span all topics; pass `-T TOPIC` to restrict to one.
- ISO date format in headings: `## YYYY-MM-DD (HH:MM) — Title`.
- `find --days N` / `--since DATE` window restriction (carried over from v1).

### Changed

- Heading format: `## YYYY-MM-DD (HH:MM) — Title` (single H2 per entry, em-dash, ISO date). Replaces the v1 `## Month D, YYYY` + `### [HH:MM] Title` two-level structure. Time uses parentheses, not square brackets, so `[[Topic#anchor]]` wikilinks don't break on the heading text.
- New entries are inserted at the top of the topic file (newest-first within each topic).
- Date parsing accepts `YYYY-MM-DD`, `YYYYMMDD`, or `MMDD`.
- Vault git repo at the vault root replaces v1's `~/.devlog/` repo. Auto-commits on every CLI write, captures direct edits on next invocation.
- `amend` preserves the existing `**Related:**` line by default; pass `--related` to rewrite it or `--no-related` to drop it.

### Removed

- `edit` subcommand. With per-topic files, opening the file in any editor (Obsidian GUI, vim, etc.) is direct and ergonomic; CLI-mediated `$EDITOR` splicing was redundant. Direct edits are still auto-captured to git.
- `[HH:MM] AMENDED:` / `[HH:MM] ADDENDUM:` inline markers on `amend`/`addend`. With the time embedded in the entry heading itself, the markers were redundant noise.
- The today-only restriction on `amend`/`addend`. Past-date entries can be modified directly.
- `--name NAME` / `$DEVLOG_NAME` author-suffix flag.
- `migrate.py` (one-shot legacy-path migration from v0).
- `AGENTS.md`. Content was a near-duplicate of `skills/tephra/SKILL.md`; merged into SKILL.md (which already carries the YAML frontmatter for Claude Code skill discovery).

### Migration

There is no automated migration path from a v1 `~/.devlog/devlog.md` file to a v2 topic-based vault — the topic-categorization step is inherently manual. The v1 data file is left untouched at `~/.devlog/devlog.md`. Approach: copy or summarize the v1 file's contents into per-topic vault files by hand (or with an LLM), then point `tephra` at the new vault via `tephra config vault PATH`.

## [1.0.1] - 2026-04-28

### Fixed

- Code-fence false positives in the markdown parser. Lines inside fenced code blocks (```` ``` ```` or `~~~`) were matched against `DATE_PAT` / `SUB_PAT`, so a body containing `### something` or `## Month D, YYYY` inside a fence would silently split the entry. Walkers in `store.py` now consult `compute_outside_fence(lines)` before triggering heading detection; pattern-checking call sites in `write.py` were updated to consult the same vector.
- Locale-sensitive date headings. `today_heading` and `parse_date_heading` previously used `strftime`/`strptime` `%B`, which reads `LC_TIME`. Running under a non-English locale produced headings the parser couldn't read back. `dates.py` now formats and parses with an explicit English `MONTHS` list, and all five `strftime("## %B %-d, %Y")` call sites use the new `format_date_heading(dt)` helper.

### Documentation

- Added `README.md` (human-facing, motivation + full usage).
- Added `AGENTS.md` (terse AI-agent reference: when to log, command tables, style/hard rules, failure modes). _Removed in v2.0.0; merged into `skills/tephra/SKILL.md`._

## [1.0.0] - 2026-04-28

First tagged release. Imports an existing single-file `~/.local/bin/devlog` script and reorganizes it into a packaged, type-hinted, lint-gated CLI.

### Added

- Subcommand surface: `add`, `show`, `find`, `recent`, `list`, `last`, `exists`, `edit`, `amend`, `addend`, `retitle`, `rm`, `undo`, `log`, `diff`.
- `--version` flag.
- Data store at `~/.devlog/devlog.md` with auto-migration from legacy `~/devlog.md` (back-compat symlink left at the old path).
- `DEVLOG_FILE` env var to override the data path.
- Atomic writes via tempfile + `os.replace` — a crash mid-write can never leave the file truncated.
- `fcntl.flock` on a separate lockfile to serialize concurrent CLI writes.
- Per-write git auto-commit to a local repo at the data dir; messages are `add: TITLE`, `amend: TITLE`, etc. Manual edits to the file are captured as `manual edit (captured)` commits on the next CLI invocation.
- `--json` output mode for `show`, `find`, `recent`, `list`, `last`.
- `--name NAME` (or `$DEVLOG_NAME`) on `add` appends an author suffix (e.g. `### [HH:MM] Title - atom`).
- `rm --dry-run` previews deletions without writing.
- Title collision rejection on `add` (same title same date errors out).
- `edit`/`amend`/`addend` accept `--date` + `--title` to target a specific subsection; default remains the newest.
- Stdin support: pass `-` as the body to `add -e`, `amend`, or `addend`.
- `MMDD` date arg resolves to the most recent past occurrence (devlog entries are always past).

### Quality

- pyproject.toml configured for ruff, ruff-format, mypy (`check_untyped_defs`), pylint (`fail-under = 10.0`), xenon (radon B-grade gate).
- Every function and module annotated and documented; pylint scores 10.00/10.
- GitHub Actions CI workflow runs all five gates on push and pull request.

[2.0.0]: https://github.com/ohshitgorillas/tephra/releases/tag/v2.0.0
[1.0.1]: https://github.com/ohshitgorillas/devlog/releases/tag/v1.0.1
[1.0.0]: https://github.com/ohshitgorillas/devlog/releases/tag/v1.0.0
