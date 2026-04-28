"""One-shot migration from legacy ~/devlog.md to ~/.devlog/devlog.md.

Idempotent: safe to call on every invocation. No-ops once the new path
exists or the env var override is set.
"""
import os

from .store import DEVLOG, git_snapshot


def migrate_if_needed():
    legacy = os.path.expanduser("~/devlog.md")
    if os.environ.get("DEVLOG_FILE"):
        return

    new_dir = os.path.dirname(DEVLOG)

    # Step 1: move legacy file into the new dir (with back-compat symlink).
    if (
        not os.path.exists(DEVLOG)
        and os.path.exists(legacy)
        and not os.path.islink(legacy)
    ):
        os.makedirs(new_dir, exist_ok=True)
        os.rename(legacy, DEVLOG)
        os.symlink(DEVLOG, legacy)

    # Step 2: ensure a git repo exists around the data, with a baseline
    # commit. Idempotent — runs once on first invocation post-upgrade,
    # then no-op forever.
    if os.path.exists(DEVLOG) and not os.path.isdir(os.path.join(new_dir, ".git")):
        git_snapshot("import existing devlog")
