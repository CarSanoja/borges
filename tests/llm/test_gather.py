from __future__ import annotations

import asyncio

import pytest

from borges.llm.client import BudgetExceeded
from borges.llm.gather import gather_cancelling


async def test_returns_results_in_order() -> None:
    async def value(n: int) -> int:
        await asyncio.sleep(0.01 * (3 - n))
        return n

    assert await gather_cancelling(value(n) for n in range(3)) == [0, 1, 2]


async def test_failure_cancels_siblings_and_raises_unwrapped() -> None:
    cancelled: list[int] = []

    async def slow(n: int) -> None:
        try:
            await asyncio.sleep(1)
        except asyncio.CancelledError:
            cancelled.append(n)
            raise

    async def boom() -> None:
        await asyncio.sleep(0.01)
        raise BudgetExceeded("cap")

    with pytest.raises(BudgetExceeded):
        await gather_cancelling([slow(1), slow(2), boom()])
    assert sorted(cancelled) == [1, 2]
