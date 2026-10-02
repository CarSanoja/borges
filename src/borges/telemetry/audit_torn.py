from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

CHUNK = 65536


def torn_path(path: Path) -> Path:
    return path.with_name(path.name + ".torn")


def _last_newline(handle: Any, size: int) -> int:
    position = size
    while position > 0:
        step = min(CHUNK, position)
        position -= step
        handle.seek(position)
        found = handle.read(step).rfind(b"\n")
        if found >= 0:
            return position + found + 1
    return 0


def _complete_record(partial: bytes) -> bool:
    try:
        return isinstance(json.loads(partial), dict)
    except ValueError:
        return False


def heal_tail(handle: Any, path: Path) -> int | None:
    """Quarantine a last line cut short by a crash; returns its byte length, or None if intact."""
    handle.seek(0, os.SEEK_END)
    size = handle.tell()
    if size == 0:
        return None
    handle.seek(size - 1)
    if handle.read(1) == b"\n":
        return None
    cut = _last_newline(handle, size)
    handle.seek(cut)
    partial = handle.read()
    if _complete_record(partial):
        handle.write(b"\n")
        handle.flush()
        return None
    with torn_path(path).open("ab") as quarantine:
        quarantine.write(partial + b"\n")
    handle.truncate(cut)
    handle.flush()
    return len(partial)
