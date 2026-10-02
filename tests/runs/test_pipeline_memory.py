from __future__ import annotations

from typing import Any

from borges.analysis.models import AnalysisPlan, CodingSummary
from borges.runs.pipeline_memory import finish_memory, prefill_code, recall_profile
from tests.runs.fakes import make_plan


class FakeMemory:
    def __init__(self, codes: dict[str, str]) -> None:
        self.codes = codes
        self.finished = False
        self.remembered = 0

    def attach(self, profile: Any) -> Any:
        return profile.model_copy(update={"name": "attached"})

    def recall_code(self, plan: AnalysisPlan, step: Any, option: Any) -> str | None:
        return self.codes.get(option.id)

    def remember_codes(self, plan: Any, garden: Any) -> None:
        self.remembered += 1

    def finish(self) -> None:
        self.finished = True

    class session:
        @staticmethod
        def usage() -> dict[str, Any]:
            return {
                "mode": "public-demo",
                "encrypted": False,
                "dataset": "abc",
                "reused": {"code": 1},
                "stored": {},
                "sources": [{"run_id": "r_old", "count": 1}],
                "dropped": 0,
            }


class FakePipeline:
    def __init__(self, memory: FakeMemory | None) -> None:
        self.memory = memory
        self.coding = CodingSummary()
        self.garden = None
        self.emitter = Emitter()


class Emitter:
    def __init__(self) -> None:
        self.events: list[tuple[str, dict[str, Any]]] = []

    async def emit(self, event_type: str, data: dict[str, Any]) -> None:
        self.events.append((event_type, data))


async def test_remembered_code_is_filled_in_and_announced_as_coded() -> None:
    plan = make_plan()
    calls: list[tuple] = []

    async def on_coded(*args: Any) -> None:
        calls.append(args)

    pipeline = FakePipeline(FakeMemory({"b": "code-b"}))
    await prefill_code(pipeline, plan, on_coded)
    assert plan.step("s1").option("b").code == "code-b"
    assert plan.step("s1").option("a").code is None
    assert calls == [("s1", "b", True, 1, None, [])]
    assert pipeline.coding.options == 1


async def test_prefill_is_a_noop_without_memory_and_keeps_existing_code() -> None:
    plan = make_plan()
    plan.step("s1").option("a").code = "own"

    async def on_coded(*args: Any) -> None:
        raise AssertionError

    await prefill_code(FakePipeline(None), plan, on_coded)
    await prefill_code(FakePipeline(FakeMemory({"a": "other"})), plan, lambda *a: on_coded())
    assert plan.step("s1").option("a").code == "own"


def test_the_profile_passes_through_memory_only_when_there_is_one() -> None:
    profile = make_plan().dataset
    assert recall_profile(FakePipeline(None), profile) is profile
    assert recall_profile(FakePipeline(FakeMemory({})), profile).name == "attached"


async def test_finish_announces_once_and_never_after_the_memory_closed() -> None:
    memory = FakeMemory({})
    pipeline = FakePipeline(memory)
    await finish_memory(pipeline, make_plan(), announce=True)
    assert memory.finished and memory.remembered == 1
    [(kind, data)] = pipeline.emitter.events
    assert kind == "memory.used" and data["reused"] == {"code": 1}
    memory.finished = True
    await finish_memory(pipeline, make_plan(), announce=True)
    assert len(pipeline.emitter.events) == 1
    await finish_memory(FakePipeline(None), None, announce=True)
