from __future__ import annotations

import os
import socket
import time
from typing import Any

UNOWNED_CUTOFF_S = 900.0


def owner_fields() -> dict[str, Any]:
    return {"owner_pid": os.getpid(), "owner_host": socket.gethostname()}


def pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return False
    return True


def is_orphan(meta: dict[str, Any], last_activity: float, now: float | None = None) -> bool:
    now = time.time() if now is None else now
    pid = meta.get("owner_pid")
    host = meta.get("owner_host")
    if isinstance(pid, int) and host == socket.gethostname():
        return not pid_alive(pid)
    return now - last_activity > UNOWNED_CUTOFF_S
