# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- `devlog find` now accepts `--days N` (restrict matches to the last
  N days) and `--since YYYYMMDD|MMDD` (restrict to entries on or
  after a specific date). The two flags are mutually exclusive.

### Changed

- `devlog addend` now always prefixes the appended paragraph with
  `[HH:MM] ADDENDUM:` so later additions read as deliberate temporal
  events.
- `devlog amend` now always prepends a `[HH:MM] AMENDED:` marker line
  to the replaced body for the same reason.

  Both behaviors are unconditional — there is no opt-out flag. The
  inline marker is always wanted; relying on `git log` to recover
  modification time loses the temporal context when reading the entry
  itself.

- `devlog amend` and `devlog addend` now refuse to operate on
  past-date entries. Stamping today's `[HH:MM]` onto a section dated
  yesterday or earlier would imply that time happened on the past
  date. Use `devlog edit -d YYYYMMDD -t "Title"` to modify older
  entries.

## [1.0.1] - 2026-04-28

### Fixed

- Code-fence false positives in the markdown parser. Lines inside
  fenced code blocks (```` ``` ```` or `~~~`) were matched against
  `DATE_PAT` / `SUB_PAT`, so a body containing `### something` or
  `## Month D, YYYY` inside a fence would silently split the entry.
  Walkers in `store.py` now consult `compute_outside_fence(lines)`
  before triggering heading detection; pattern-checking call sites in
  `write.py` were updated to consult the same vector.
- Locale-sensitive date headings. `today_heading` and
  `parse_date_heading` previously used `strftime`/`strptime` `%B`,
  which reads `LC_TIME`. Running under a non-English locale produced
  headings the parser couldn't read back. `dates.py` now formats and
  parses with an explicit English `MONTHS` list, and all five
  `strftime("## %B %-d, %Y")` call sites use the new
  `format_date_heading(dt)` helper.

### Documentation

- Added `README.md` (human-facing, motivation + full usage).
- Added `AGENTS.md` (terse AI-agent reference: when to log, command
  tables, style/hard rules, failure modes).

## [1.0.0] - 2026-04-28

First tagged release. Imports an existing single-file `~/.local/bin/devlog`
script and reorganizes it into a packaged, type-hinted, lint-gated CLI.

### Added

- Subcommand surface: `add`, `show`, `find`, `recent`, `list`, `last`,
  `exists`, `edit`, `amend`, `addend`, `retitle`, `rm`, `undo`, `log`, `diff`.
- `--version` flag.
- Data store at `~/.devlog/devlog.md` with auto-migration from legacy
  `~/devlog.md` (back-compat symlink left at the old path).
- `DEVLOG_FILE` env var to override the data path.
- Atomic writes via tempfile + `os.replace` — a crash mid-write can never
  leave the file truncated.
- `fcntl.flock` on a separate lockfile to serialize concurrent CLI writes.
- Per-write git auto-commit to a local repo at the data dir; messages are
  `add: TITLE`, `amend: TITLE`, etc. Manual edits to the file are captured
  as `manual edit (captured)` commits on the next CLI invocation.
- `--json` output mode for `show`, `find`, `recent`, `list`, `last`.
- `--name NAME` (or `$DEVLOG_NAME`) on `add` appends an author suffix
  (e.g. `### [HH:MM] Title - atom`).
- `rm --dry-run` previews deletions without writing.
- Title collision rejection on `add` (same title same date errors out).
- `edit`/`amend`/`addend` accept `--date` + `--title` to target a specific
  subsection; default remains the newest.
- Stdin support: pass `-` as the body to `add -e`, `amend`, or `addend`.
- `MMDD` date arg resolves to the most recent past occurrence (devlog
  entries are always past).

### Quality

- pyproject.toml configured for ruff, ruff-format, mypy
  (`check_untyped_defs`), pylint (`fail-under = 10.0`), xenon (radon
  B-grade gate).
- Every function and module annotated and documented; pylint scores
  10.00/10.
- GitHub Actions CI workflow runs all five gates on push and pull request.

[1.0.1]: https://github.com/ohshitgorillas/devlog/releases/tag/v1.0.1
[1.0.0]: https://github.com/ohshitgorillas/devlog/releases/tag/v1.0.0
