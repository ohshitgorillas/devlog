# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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

[1.0.0]: https://github.com/ohshitgorillas/devlog/releases/tag/v1.0.0
