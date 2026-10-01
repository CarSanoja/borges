from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

from borges.config import Settings


def sweep_sandboxes(settings: Settings) -> None:
    root = Path(settings.borges_home) / "sandboxes"
    if not root.is_dir():
        return
    for child in root.iterdir():
        shutil.rmtree(child, ignore_errors=True)


def reconcile(settings: Settings, store: Any, orchestrator: Any) -> None:
    active = set(getattr(orchestrator, "tasks", {}))
    store.interrupt_running(active)
    sweep_sandboxes(settings)
