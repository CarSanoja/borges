from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Iterable

from borges.llm.client import BudgetExceeded


async def gather_cancelling[T](awaitables: Iterable[Awaitable[T]]) -> list[T]:
    """Run awaitables together; the first failure cancels the rest and is raised unwrapped."""
    try:
        async with asyncio.TaskGroup() as group:
            tasks = [group.create_task(_wrap(a)) for a in awaitables]
    except BaseExceptionGroup as group_error:
        errors = group_error.exceptions
        budget = next((e for e in errors if isinstance(e, BudgetExceeded)), None)
        raise (budget or errors[0]) from None
    return [task.result() for task in tasks]


async def _wrap[T](awaitable: Awaitable[T]) -> T:
    return await awaitable
