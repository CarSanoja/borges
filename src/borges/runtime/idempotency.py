from __future__ import annotations

import hashlib
import re

from borges.config import Settings
from borges.runs.models import RunRequest
from borges.runtime.queue import IdempotencyKey

HEADER = "Idempotency-Key"
KEY_PATTERN = re.compile(r"[A-Za-z0-9._:\-]{1,128}")
EXPLICIT_WINDOW_S = 24 * 3600.0


def valid_header(value: str) -> bool:
    return KEY_PATTERN.fullmatch(value) is not None


def _digest(*parts: str) -> str:
    return hashlib.sha256("\x1f".join(parts).encode("utf-8")).hexdigest()


def explicit_key(principal_id: str, value: str) -> IdempotencyKey:
    return IdempotencyKey(_digest("explicit", principal_id, value), False, EXPLICIT_WINDOW_S)


def derived_key(owner_key: str, request: RunRequest, settings: Settings) -> IdempotencyKey:
    body = request.model_dump_json(exclude_none=True)
    return IdempotencyKey(
        _digest("derived", owner_key, body), True, settings.borges_idempotency_window_s
    )


def schedule_key(schedule_id: str, slot: float) -> IdempotencyKey:
    return IdempotencyKey(_digest("schedule", schedule_id, f"{slot:.3f}"), False, EXPLICIT_WINDOW_S)
