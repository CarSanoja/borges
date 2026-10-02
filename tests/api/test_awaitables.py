from __future__ import annotations

from borges.api.awaitables import resolve


async def test_resolve_awaits_awaitables_and_passes_values_through() -> None:
    async def later() -> int:
        return 3

    assert await resolve(later()) == 3
    assert await resolve(4) == 4
