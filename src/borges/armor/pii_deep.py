from __future__ import annotations

from collections import Counter
from typing import Any

from borges.armor.pii import find_pii, redact_pii


def redact_deep(value: Any, counts: Counter[str] | None = None) -> Any:
    if isinstance(value, str):
        if counts is not None:
            counts.update(match.kind for match in find_pii(value))
        return redact_pii(value)
    if isinstance(value, dict):
        return {key: redact_deep(item, counts) for key, item in value.items()}
    if isinstance(value, list):
        return [redact_deep(item, counts) for item in value]
    if isinstance(value, tuple):
        return tuple(redact_deep(item, counts) for item in value)
    return value
