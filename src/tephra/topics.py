"""Topic discovery, validation, creation, and vault config."""

from __future__ import annotations

import os
import re
import sys

from .store import (
    auto_sync_config_path,
    config_path,
    default_folder_path,
    ensure_vault,
    folder_dir,
    git_snapshot,
    read_auto_sync,
    read_default_folder,
    read_sync_metric_path,
    sync_metric_config_path,
    topic_path,
    vault_dir,
    vault_source,
    write_auto_sync,
    write_config_default_folder,
    write_config_vault,
    write_lines,
    write_lock,
    write_sync_metric_path,
)

_TOPIC_NAME_PAT = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]*$")
_FOLDER_NAME_PAT = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]*$")


def parse_topic_arg(arg: str) -> tuple[str | None, str | None]:
    """Parse a ``-T`` value into ``(folder, topic)``.

    Forms:
      - ``Topic``           → (default_folder, "Topic")
      - ``Folder:Topic``    → ("Folder", "Topic")
      - ``Folder:``         → ("Folder", None) — folder-scope, all topics (reads only)
    """
    if ":" not in arg:
        topic = arg.strip()
        if not topic:
            sys.exit("-T value is empty")
        return read_default_folder(), topic
    folder, topic = arg.split(":", 1)
    folder = folder.strip()
    topic = topic.strip()
    if not folder:
        sys.exit(f"-T '{arg}': folder required (form: 'Folder:Topic' or 'Folder:')")
    return folder, (topic or None)


def _list_md_in(d: str) -> list[str]:
    if not os.path.isdir(d):
        return []
    out: list[str] = []
    for name in os.listdir(d):
        if name.startswith("."):
            continue
        if not name.endswith(".md"):
            continue
        if not os.path.isfile(os.path.join(d, name)):
            continue
        out.append(name[:-3])
    return sorted(out)


def list_topics(folder: str | None) -> list[str]:
    """Return sorted topic names in ``folder`` (None = vault root)."""
    return _list_md_in(folder_dir(folder))


def iter_all_topic_paths() -> list[tuple[str | None, str, str]]:
    """Return ``(folder, topic, abs_path)`` for every topic file in the vault."""
    out: list[tuple[str | None, str, str]] = []
    for t in list_topics(None):
        out.append((None, t, topic_path(t, None)))
    for f in list_folders():
        for t in list_topics(f):
            out.append((f, t, topic_path(t, f)))
    return out


def list_folders() -> list[str]:
    """Return sorted folder names (subdirectories of vault, excluding hidden/_*)."""
    d = vault_dir()
    if not os.path.isdir(d):
        return []
    out: list[str] = []
    for name in os.listdir(d):
        if name.startswith(".") or name.startswith("_"):
            continue
        if os.path.isdir(os.path.join(d, name)):
            out.append(name)
    return sorted(out)


def _folder_label(folder: str | None) -> str:
    return folder if folder else "<root>"


def validate_topic(folder: str | None, topic: str) -> None:
    """Exit if ``topic`` is not a known topic in ``folder``."""
    topics = list_topics(folder)
    if topic in topics:
        return
    label = _folder_label(folder)
    if not topics:
        sys.exit(
            f"No topics in {label} ({folder_dir(folder)}). "
            f"Create one with `tephra topic add {topic}`"
            + (f" -F {folder}" if folder else "")
            + "."
        )
    sys.exit(
        f"Unknown topic '{topic}' in {label}. Known: {', '.join(topics)}. "
        f"Create with `tephra topic add {topic}`"
        + (f" -F {folder}" if folder else "")
        + "."
    )


def create_topic(name: str, folder: str | None = None) -> None:
    """Create ``{folder}/{name}.md`` with an H1 heading. Refuses if it exists."""
    if not _TOPIC_NAME_PAT.match(name):
        sys.exit(
            f"Invalid topic name '{name}'. "
            f"Use letters, digits, '-' and '_' only; must start alphanumeric."
        )
    if folder and not _FOLDER_NAME_PAT.match(folder):
        sys.exit(
            f"Invalid folder name '{folder}'. "
            f"Use letters, digits, '-' and '_' only; must start alphanumeric."
        )
    ensure_vault()
    os.makedirs(folder_dir(folder), exist_ok=True)
    path = topic_path(name, folder)
    if os.path.exists(path):
        sys.exit(f"Topic '{name}' already exists at {path}")
    with write_lock():
        write_lines(path, [f"# {name}\n"])
        git_snapshot(f"topic add: {_folder_label(folder)}/{name}")
    print(f"Created topic '{name}' at {path}")


def cmd_topic_list(folder: str | None = None) -> None:
    """Print known topics in ``folder`` (None = default), one per line."""
    if folder is None:
        folder = read_default_folder()
    topics = list_topics(folder)
    if not topics:
        print(f"No topics in {_folder_label(folder)} ({folder_dir(folder)})")
        return
    for t in topics:
        print(t)


def cmd_topic_add(name: str, folder: str | None = None) -> None:
    """Create a new topic file."""
    if folder is None:
        folder = read_default_folder()
    create_topic(name, folder)


def cmd_folder_list() -> None:
    """Print folder names (subdirectories of vault), one per line."""
    folders = list_folders()
    if not folders:
        print(f"No folders in vault {vault_dir()}")
        return
    for f in folders:
        print(f)


def cmd_config_default_folder(folder: str | None) -> None:
    """Persist or clear the default folder."""
    write_config_default_folder(folder)
    if folder:
        print(f"Default folder set to '{folder}'")
    else:
        print("Default folder cleared (writes go to vault root)")


def cmd_config_vault(path: str) -> None:
    """Persist ``path`` as the vault location in the user config file."""
    write_config_vault(path)
    resolved, _ = vault_source()
    print(f"Wrote vault path to {config_path()}")
    print(f"Vault: {resolved}")


def cmd_config_show() -> None:
    """Print the resolved vault path and its source."""
    resolved, source = vault_source()
    print(f"Vault: {resolved}")
    print(f"Source: {source}")
    print(f"Config file: {config_path()}")
    folder = read_default_folder()
    print(f"Default folder: {folder if folder else '<root>'}")
    print(f"Default folder config: {default_folder_path()}")
    print(f"Auto-sync: {'on' if read_auto_sync() else 'off'}")
    print(f"Auto-sync config: {auto_sync_config_path()}")
    metric = read_sync_metric_path()
    print(f"Sync metric: {metric if metric else '<unset>'}")
    print(f"Sync metric config: {sync_metric_config_path()}")


def cmd_config_auto_sync(value: str) -> None:
    """Persist the auto-sync toggle. Accepts ``on`` or ``off`` (case-insensitive)."""
    norm = value.strip().lower()
    if norm not in ("on", "off"):
        sys.exit("auto-sync value must be 'on' or 'off'")
    write_auto_sync(norm == "on")
    print(f"Auto-sync set to '{norm}'")


def cmd_config_sync_metric(path: str) -> None:
    """Persist or clear the sync-metric output path. Empty string clears."""
    write_sync_metric_path(path or None)
    if path:
        print(f"Sync metric path set to '{path}'")
    else:
        print("Sync metric path cleared")


def cmd_config_path() -> None:
    """Print the resolved vault path with no decoration (for shell scripting)."""
    print(vault_dir())
