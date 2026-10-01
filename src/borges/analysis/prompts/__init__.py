from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel


def compact_json(value: Any) -> str:
    if isinstance(value, BaseModel):
        value = value.model_dump(mode="json", exclude_none=True)
    return json.dumps(value, separators=(",", ":"), ensure_ascii=False, default=str)


def messages(system: str, user: str) -> list[dict[str, str]]:
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]
