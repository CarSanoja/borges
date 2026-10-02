from __future__ import annotations

from types import SimpleNamespace

import pytest

from borges.llm.client import BudgetExceeded
from borges.runs.pipeline_stages import MAX_COMBINATIONS_PER_LEVEL, tolerate_budget


def fake_pipeline() -> SimpleNamespace:
    return SimpleNamespace(search=SimpleNamespace(budget_exhausted=False), caveats=[])


async def test_budget_exhaustion_becomes_a_caveat() -> None:
    pipeline = fake_pipeline()

    async def work() -> None:
        raise BudgetExceeded("run cap")

    await tolerate_budget(pipeline, work(), "The flips stopped early")
    assert pipeline.search.budget_exhausted is True
    assert pipeline.caveats == [
        "The flips stopped early because the spend or run cap was reached: run cap"
    ]


async def test_other_errors_still_propagate() -> None:
    async def work() -> None:
        raise ValueError("boom")

    with pytest.raises(ValueError):
        await tolerate_budget(fake_pipeline(), work(), "x")


async def test_clean_work_leaves_the_search_untouched() -> None:
    pipeline = fake_pipeline()

    async def work() -> None:
        return None

    await tolerate_budget(pipeline, work(), "x")
    assert pipeline.search.budget_exhausted is False and pipeline.caveats == []
    assert MAX_COMBINATIONS_PER_LEVEL == 10
