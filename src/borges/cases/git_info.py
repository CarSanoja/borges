from __future__ import annotations

import os
import subprocess
from pathlib import Path

GIT_TIMEOUT_S = 5.0


def _git(args: list[str], cwd: Path) -> str | None:
    try:
        done = subprocess.run(
            ["git", *args],
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=GIT_TIMEOUT_S,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return done.stdout if done.returncode == 0 else None


def current_commit(cwd: Path) -> str | None:
    override = os.environ.get("BORGES_COMMIT", "").strip()
    if override:
        return override
    out = _git(["rev-parse", "--short", "HEAD"], cwd)
    return out.strip() or None if out is not None else None


def src_is_dirty(cwd: Path) -> bool | None:
    out = _git(["status", "--porcelain", "--untracked-files=no", "--", "src"], cwd)
    return None if out is None else bool(out.strip())
