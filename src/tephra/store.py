"""Vault location, file I/O, parsing, git ops, locking."""

from __future__ import annotations

import contextlib
import fcntl
import os
import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from typing import Iterator

ENTRY_PAT = re.compile(r"^## (\d{4}-\d{2}-\d{2})(?: \((\d{2}:\d{2})\))? — (.+?)\s*$")
H1_PAT = re.compile(r"^# (.+?)\s*$")
RELATED_PAT = re.compile(r"^\*\*Related:\*\*\s*(.+?)\s*$")
_FENCE_PAT = re.compile(r"^(?:```|~~~)")


def vault_dir() -> str:
    """Return the configured vault directory.

    Resolution order:
      1. ``$TEPHRA_VAULT`` if set
      2. ``$XDG_DATA_HOME/tephra/vault``
      3. ``$HOME/.local/share/tephra/vault``
    """
    explicit = os.environ.get("TEPHRA_VAULT")
    if explicit:
        return os.path.expanduser(explicit)
    xdg = os.environ.get("XDG_DATA_HOME") or os.path.expanduser("~/.local/share")
    return os.path.join(xdg, "tephra", "vault")


def lockfile() -> str:
    """Return the path to the per-vault lockfile."""
    return os.path.join(vault_dir(), ".tephra.lock")


def topic_path(topic: str) -> str:
    """Return the markdown file path for ``topic`` (no validation)."""
    return os.path.join(vault_dir(), f"{topic}.md")


def ensure_vault() -> None:
    """Create the vault directory if absent."""
    os.makedirs(vault_dir(), exist_ok=True)


@contextlib.contextmanager
def write_lock() -> Iterator[None]:
    """Hold an exclusive flock for the duration of a read-modify-write op."""
    ensure_vault()
    path = lockfile()
    fd = os.open(path, os.O_RDWR | os.O_CREAT, 0o600)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
        yield
    finally:
        fcntl.flock(fd, fcntl.LOCK_UN)
        os.close(fd)


def read_lines(path: str) -> list[str]:
    """Return file contents as a list of lines (with newlines)."""
    with open(path, encoding="utf-8") as f:
        return f.readlines()


def write_lines(path: str, lines: list[str]) -> None:
    """Atomic write via tempfile + rename in the same directory."""
    d = os.path.dirname(path) or "."
    os.makedirs(d, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".tephra.", dir=d)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.writelines(lines)
        os.replace(tmp, path)
    except Exception:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def compute_outside_fence(lines: list[str]) -> list[bool]:
    """Per-line booleans: True iff the line is outside any fenced code block."""
    out: list[bool] = []
    inside = False
    for line in lines:
        if _FENCE_PAT.match(line):
            out.append(False)
            inside = not inside
        else:
            out.append(not inside)
    return out


@dataclass
class Entry:
    """One H2-delimited entry inside a topic file."""

    topic: str
    date: str
    time: str | None
    title: str
    start: int
    end: int


def parse_entries(topic: str, lines: list[str]) -> list[Entry]:
    """Return all entries in ``lines`` for ``topic``."""
    outside = compute_outside_fence(lines)
    starts: list[tuple[int, str, str | None, str]] = []
    for i, line in enumerate(lines):
        if not outside[i]:
            continue
        m = ENTRY_PAT.match(line)
        if m:
            starts.append((i, m.group(1), m.group(2), m.group(3)))
    entries: list[Entry] = []
    for idx, (start, date, time, title) in enumerate(starts):
        end = starts[idx + 1][0] if idx + 1 < len(starts) else len(lines)
        entries.append(Entry(topic, date, time, title, start, end))
    return entries


def find_entry(topic: str, lines: list[str], date: str, title: str) -> Entry | None:
    """Return the entry matching ``date`` and ``title`` exactly, or None."""
    for e in parse_entries(topic, lines):
        if e.date == date and e.title == title:
            return e
    return None


def find_first_entry(lines: list[str]) -> int | None:
    """Index of the first H2 entry in ``lines``, or None."""
    outside = compute_outside_fence(lines)
    for i, line in enumerate(lines):
        if outside[i] and ENTRY_PAT.match(line):
            return i
    return None


def find_h1_end(lines: list[str]) -> int:
    """Return the line index immediately after the H1 block.

    Treats the H1 block as the first ``# Foo`` line plus a single trailing
    blank line if present. If no H1 is present, returns 0.
    """
    if not lines:
        return 0
    if not H1_PAT.match(lines[0]):
        return 0
    if len(lines) > 1 and not lines[1].strip():
        return 2
    return 1


def insertion_point(lines: list[str]) -> int:
    """Line index where a new entry should be inserted (above first H2)."""
    first = find_first_entry(lines)
    if first is not None:
        return first
    return find_h1_end(lines)


def _git(repo: str, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", repo, *args],
        check=check,
        capture_output=True,
        text=True,
    )


def init_repo(repo: str) -> None:
    """Init a git repo at ``repo`` if absent. Sets a local identity if missing."""
    os.makedirs(repo, exist_ok=True)
    if os.path.isdir(os.path.join(repo, ".git")):
        return
    _git(repo, "init", "-q", "-b", "main")
    if not _git(repo, "config", "user.email", check=False).stdout.strip():
        _git(repo, "config", "user.email", "tephra@localhost")
        _git(repo, "config", "user.name", "tephra")


def capture_manual_edits() -> None:
    """Commit any uncommitted vault changes as 'manual edit (captured)'."""
    repo = vault_dir()
    if not os.path.isdir(os.path.join(repo, ".git")):
        return
    try:
        diff = _git(repo, "diff", "--quiet", "HEAD", check=False)
        untracked = _git(
            repo, "ls-files", "--others", "--exclude-standard", check=False
        ).stdout.strip()
        if diff.returncode == 0 and not untracked:
            return
        _git(repo, "add", "-A")
        cached = _git(repo, "diff", "--cached", "--quiet", check=False)
        if cached.returncode == 0:
            return
        _git(repo, "commit", "-q", "-m", "manual edit (captured)")
        print(f"note: captured manual edit in {repo}", file=sys.stderr)
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        print(f"warning: capture_manual_edits failed: {e}", file=sys.stderr)


def git_snapshot(message: str) -> None:
    """Stage everything in the vault and commit. Best-effort; no-op if clean."""
    repo = vault_dir()
    try:
        init_repo(repo)
        _git(repo, "add", "-A")
        diff = _git(repo, "diff", "--cached", "--quiet", check=False)
        if diff.returncode != 0:
            _git(repo, "commit", "-q", "-m", message)
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        print(f"warning: git snapshot failed: {e}", file=sys.stderr)
