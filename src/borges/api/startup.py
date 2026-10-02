from __future__ import annotations

import logging
import shutil
from pathlib import Path
from typing import Any

from borges.config import Settings
from borges.identity.store_key import UNKEYED_NOTICE, store_key

logger = logging.getLogger(__name__)


def sweep_sandboxes(settings: Settings) -> None:
    root = Path(settings.borges_home) / "sandboxes"
    if not root.is_dir():
        return
    for child in root.iterdir():
        shutil.rmtree(child, ignore_errors=True)


def reconcile(settings: Settings, store: Any, orchestrator: Any, runtime: Any = None) -> None:
    active = set(getattr(orchestrator, "tasks", {}))
    if runtime is not None:
        active |= runtime.known_run_ids()
    live_elsewhere = getattr(store, "live_elsewhere", lambda _active: [])(active)
    store.interrupt_running(active)
    if not live_elsewhere:
        sweep_sandboxes(settings)


def warn_unkeyed(settings: Settings) -> bool:
    if store_key(settings):
        return False
    logger.warning(
        "key store and registry chains are %s; set BORGES_STORE_KEY (or BORGES_AUDIT_ANCHOR_KEY)",
        UNKEYED_NOTICE,
    )
    return True
