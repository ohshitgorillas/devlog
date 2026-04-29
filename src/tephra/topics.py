"""Topic discovery, validation, creation."""

from __future__ import annotations

import os
import re
import sys

from .store import (
    ensure_vault,
    git_snapshot,
    topic_path,
    vault_dir,
    write_lines,
    write_lock,
)

_TOPIC_NAME_PAT = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]*$")


def list_topics() -> list[str]:
    """Return sorted list of topic names found in the vault.

    Topics are top-level ``*.md`` files. Hidden files and any file under a
    subdirectory (e.g. ``_archive/``) are excluded.
    """
    d = vault_dir()
    if not os.path.isdir(d):
        return []
    out: list[str] = []
    for name in os.listdir(d):
        if name.startswith("."):
            continue
        if not name.endswith(".md"):
            continue
        full = os.path.join(d, name)
        if not os.path.isfile(full):
            continue
        out.append(name[:-3])
    return sorted(out)


def validate_topic(name: str) -> None:
    """Exit if ``name`` is not a known topic."""
    topics = list_topics()
    if name in topics:
        return
    if not topics:
        sys.exit(
            f"No topics in vault {vault_dir()}. "
            f"Create one with `tephra topic add {name}`."
        )
    sys.exit(
        f"Unknown topic '{name}'. Known: {', '.join(topics)}. "
        f"Create with `tephra topic add {name}`."
    )


def create_topic(name: str) -> None:
    """Create ``{name}.md`` with an H1 heading. Refuses if it already exists."""
    if not _TOPIC_NAME_PAT.match(name):
        sys.exit(
            f"Invalid topic name '{name}'. "
            f"Use letters, digits, '-' and '_' only; must start alphanumeric."
        )
    ensure_vault()
    path = topic_path(name)
    if os.path.exists(path):
        sys.exit(f"Topic '{name}' already exists at {path}")
    with write_lock():
        write_lines(path, [f"# {name}\n"])
        git_snapshot(f"topic add: {name}")
    print(f"Created topic '{name}' at {path}")


def cmd_topic_list() -> None:
    """Print known topics, one per line."""
    topics = list_topics()
    if not topics:
        print(f"No topics in vault {vault_dir()}")
        return
    for t in topics:
        print(t)


def cmd_topic_add(name: str) -> None:
    """Create a new topic file."""
    create_topic(name)
