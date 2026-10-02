from __future__ import annotations

import re
from typing import Any

REDACTED = "[redacted]"
_EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
_LONG_DIGITS = re.compile(r"\d{9,}")


def redact_text(value: str) -> str:
    return _LONG_DIGITS.sub(REDACTED, _EMAIL.sub(REDACTED, value))


def redact_value(value: Any) -> Any:
    if isinstance(value, str):
        return redact_text(value)
    if isinstance(value, dict):
        return {key: redact_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return [redact_value(item) for item in value]
    return value
