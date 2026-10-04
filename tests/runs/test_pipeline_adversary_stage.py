from __future__ import annotations

from contextlib import asynccontextmanager
from types import SimpleNamespace
from typing import Any

import pytest

from borges.llm.client import LLMError
from borges.runs import pipeline_stages
from borges.runs.pipeline_stages import NO_ADVERSARY, run_adversary
from tests.analysis.fakes import make_option, make_plan


def stage_pipeline() -> SimpleNamespace:
    @asynccontextmanager
    async def stage(name: str):
        yield

    return SimpleNamespace(
        stage=stage,
        smoke=None,
        llm=None,
        emitter=None,
        judged=None,
        armor_stage=None,
        memory=None,
        caveats=[],
    )


async def test_an_adversary_that_adds_nothing_is_reported(monkeypatch: pytest.MonkeyPatch) -> None:
    async def round_without_options(*_: Any) -> list[Any]:
        return []

    monkeypatch.setattr(pipeline_stages, "run_adversary_round", round_without_options)
    pipeline = stage_pipeline()
    await run_adversary(pipeline, make_plan(), None, None)
    assert pipeline.caveats == [NO_ADVERSARY]


async def test_an_adversary_option_in_the_plan_needs_no_caveat(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    plan = make_plan()

    async def round_with_option(*_: Any) -> list[Any]:
        option = make_option("adv_clip").model_copy(update={"origin": "adversary"})
        plan.step("d1").options.append(option)
        return []

    monkeypatch.setattr(pipeline_stages, "run_adversary_round", round_with_option)
    pipeline = stage_pipeline()
    await run_adversary(pipeline, plan, None, None)
    assert pipeline.caveats == []


async def test_a_failed_adversary_call_is_reported(monkeypatch: pytest.MonkeyPatch) -> None:
    async def failing(*_: Any) -> list[Any]:
        raise LLMError("adversary: invalid output")

    monkeypatch.setattr(pipeline_stages, "run_adversary_round", failing)
    pipeline = stage_pipeline()
    await run_adversary(pipeline, make_plan(), None, None)
    assert pipeline.caveats == [
        "The adversary stage failed and was skipped: adversary: invalid output"
    ]
