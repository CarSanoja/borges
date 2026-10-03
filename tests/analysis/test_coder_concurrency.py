from __future__ import annotations

import pytest

from borges.analysis import coder
from borges.analysis.coder import code_plan
from borges.analysis.schemas import CoderOutput
from tests.analysis.fakes import FakeLLM, make_plan

GOOD = "def apply(df, ctx):\n    return df"


def guard(bad: set[str]):
    def check(code: str, kind: str, intent: str = "") -> list[str]:
        return [f"bad: {code}"] if code in bad else []

    return check


@pytest.fixture(autouse=True)
def passing_guard(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(coder, "check_code", guard(set()))


async def test_code_plan_failure_cancels_in_flight_siblings() -> None:
    import asyncio

    from borges.llm.client import BudgetExceeded

    started: list[str] = []
    finished: list[str] = []

    class Failing(FakeLLM):
        async def complete(self, role, messages, *, key, **kwargs):
            started.append(key)
            if key == "coder:d1.keep":
                raise BudgetExceeded("cap")
            await asyncio.sleep(0.2)
            finished.append(key)
            return await super().complete(role, messages, key=key, **kwargs)

    keys = ["coder:d1.keep", "coder:d1.trim", "coder:m1.ols", "coder:m1.welch"]
    llm = Failing({k: CoderOutput(code="C") for k in keys})
    with pytest.raises(BudgetExceeded):
        await code_plan(llm, make_plan())
    await asyncio.sleep(0.3)
    assert len(started) == 4 and finished == []


async def test_code_plan_respects_concurrency() -> None:
    import asyncio

    active = 0
    peak = 0

    class Slow(FakeLLM):
        async def complete(self, *args, **kwargs):
            nonlocal active, peak
            active += 1
            peak = max(peak, active)
            await asyncio.sleep(0.01)
            active -= 1
            return await super().complete(*args, **kwargs)

    keys = ["coder:d1.keep", "coder:d1.trim", "coder:m1.ols", "coder:m1.welch"]
    llm = Slow({k: CoderOutput(code="C") for k in keys})
    await code_plan(llm, make_plan(), concurrency=2)
    assert peak == 2
