"""``tephra skill``: print or install the bundled Claude Code skill file."""

from __future__ import annotations

import os
import sys
from importlib.resources import files

_SKILL_RESOURCE = files("tephra").joinpath("skills/tephra/SKILL.md")
_REL_INSTALL_PATH = os.path.join("skills", "tephra", "SKILL.md")


def _read_skill() -> str:
    return _SKILL_RESOURCE.read_text(encoding="utf-8")


def _default_install_root() -> str:
    project_dir = os.environ.get("CLAUDE_PROJECT_DIR")
    if project_dir:
        return os.path.join(project_dir, ".claude")
    return os.path.join(os.path.expanduser("~"), ".claude")


def cmd_skill_print() -> None:
    """Write the bundled SKILL.md to stdout."""
    sys.stdout.write(_read_skill())


def cmd_skill_path() -> None:
    """Print the on-disk path of the bundled SKILL.md."""
    print(str(_SKILL_RESOURCE))


def cmd_skill_install(target: str | None) -> None:
    """Copy the bundled SKILL.md into a Claude Code skills directory."""
    root = target if target else _default_install_root()
    dest = os.path.join(root, _REL_INSTALL_PATH)
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    with open(dest, "w", encoding="utf-8") as f:
        f.write(_read_skill())
    print(f"installed: {dest}")
