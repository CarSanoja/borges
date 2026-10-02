from __future__ import annotations

import inspect
from typing import Any


async def resolve(value: Any) -> Any:
    return await value if inspect.isawaitable(value) else value
