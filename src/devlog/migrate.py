"""One-shot migration from legacy ~/devlog.md to ~/.devlog/devlog.md.

Idempotent: safe to call on every invocation. No-ops once the new path
exists or the env var override is set.
"""
import os

from .store import DEVLOG


def migrate_if_needed():
    legacy = os.path.expanduser("~/devlog.md")
    if os.environ.get("DEVLOG_FILE"):
        return
    if os.path.exists(DEVLOG):
        return
    if not os.path.exists(legacy) or os.path.islink(legacy):
        return

    new_dir = os.path.dirname(DEVLOG)
    os.makedirs(new_dir, exist_ok=True)
    os.rename(legacy, DEVLOG)
    # Leave a symlink at the old path so any external tooling
    # (rsync jobs, manual cat, etc.) still finds the file.
    os.symlink(DEVLOG, legacy)
