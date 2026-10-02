from __future__ import annotations

from typing import Any

import pytest

from borges.analysis import coder
from borges.analysis.coder import code_plan
from borges.analysis.coder_smoke import SmokeConfig
from borges.analysis.models import Judgement, Proposal
from borges.analysis.schemas import CoderOutput, ReviewerOutput, ReviewVerdict
from borges.analysis.smoke_review import llm_reviewer
from borges.runs import adversary_round
from borges.runs.adversary_round import run_adversary_round
from tests.analysis.fakes import FakeLLM, make_option
from tests.analysis.smoke_fakes import ScriptBackend, effects
from tests.analysis.test_smoke_orientation import (
    CONTROL,
    DOWN,
    ESTIMATE,
    TREAT,
    UP,
    Recorder,
    data_bytes,
    feature_plan,
)

ADV_REVERSED = "def apply(df, ctx):\n    adv_reversed = 1\n    return df"
ADV_FIXED = "def apply(df, ctx):\n    adv_fixed = 1\n    return df"
HALF = effects("treated", UP, rows=(100, 50), dropped={"variant": {"control": 50}})


class Emitter:
    def __init__(self) -> None:
        self.events: list[tuple[str, dict[str, Any]]] = []

    async def emit(self, event_type: str, data: dict[str, Any]) -> None:
        self.events.append((event_type, data))


class Runner:
    def __init__(self) -> None:
        self.ran: list[Any] = []

    async def run_many(self, choices: list[dict[str, str]], kind: str) -> list[Any]:
        self.ran.extend(choices)
        return []


@pytest.fixture(autouse=True)
def passing_guard(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(coder, "check_code", lambda code, kind: [])


def script(adversary: dict | None) -> list[tuple[str, dict | None]]:
    return [
        ("treat_variant", effects("treated", UP)),
        ("control_variant", effects("treated", UP)),
        ("adv_reversed", adversary),
        ("adv_fixed", effects("treated", UP)),
    ]


async def prepare(
    monkeypatch: pytest.MonkeyPatch, adversary: dict | None, extra: dict[str, Any] | None = None
):
    verdicts = ReviewerOutput(
        verdicts=[ReviewVerdict(option_id="adv", faithful=True, changes_estimand=False, problem="")]
    )
    base = {"coder:f1.treat": TREAT, "coder:f1.control": CONTROL, "coder:m1.ols": ESTIMATE}
    responses: dict[str, Any] = {k: CoderOutput(code=v) for k, v in base.items()}
    responses["reviewer:f1"] = verdicts
    responses.update(extra or {})
    llm = FakeLLM(responses)
    plan = feature_plan(["treated"])
    recorder = Recorder()
    config = SmokeConfig(
        ScriptBackend(script(adversary)),
        data_bytes(),
        recorder,
        reviewer=llm_reviewer(llm, plan),
    )
    coded = await code_plan(llm, plan, smoke=config)

    async def propose(*args: Any) -> list[Proposal]:
        return [Proposal(step_id="f1", option=make_option("adv"))]

    async def judge(*args: Any) -> Judgement:
        return Judgement(defensibility=0.8, accepted=True, reason="ok", source="http://s")

    async def code_option(*args: Any) -> str:
        return ADV_REVERSED

    monkeypatch.setattr(adversary_round, "propose_options", propose)
    monkeypatch.setattr(adversary_round, "judge_option", judge)
    monkeypatch.setattr(adversary_round, "code_option", code_option)
    return llm, coded, config, recorder


async def test_reversed_adversary_option_is_repaired_and_runs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    extra = {"coder:f1.adv:smoke1": CoderOutput(code=ADV_FIXED)}
    llm, plan, config, recorder = await prepare(monkeypatch, effects("treated", DOWN), extra)
    runner, emitter = Runner(), Emitter()
    await run_adversary_round(llm, plan, runner, emitter, None, config)
    prompt = next(c for c in llm.calls if c.key == "coder:f1.adv:smoke1").messages[1]["content"]
    assert "column 'treated' is reversed relative to the default option" in prompt
    assert plan.step("f1").option("adv").code == ADV_FIXED
    assert runner.ran == [{"f1": "adv", "m1": "ols"}]
    assert [e[2] for e in recorder.events if e[1] == "adv"] == ["repaired"]


async def test_still_reversed_adversary_option_is_dropped_and_not_run(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    extra = {
        "coder:f1.adv:smoke1": CoderOutput(code=ADV_REVERSED),
        "coder:f1.adv:smoke2": CoderOutput(code=ADV_REVERSED),
    }
    llm, plan, config, recorder = await prepare(monkeypatch, effects("treated", DOWN), extra)
    runner, emitter = Runner(), Emitter()
    await run_adversary_round(llm, plan, runner, emitter, None, config)
    assert runner.ran == []
    assert [o.id for o in plan.step("f1").options] == ["treat", "control"]
    coded = [d for t, d in emitter.events if t == "option.coded" and d["option_id"] == "adv"]
    assert len(coded) == 1 and coded[0]["ok"] is False
    assert "is reversed relative to the default" in coded[0]["error"]


async def test_faithful_adversary_option_runs_and_reviewer_sees_effects(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    llm, plan, config, _ = await prepare(monkeypatch, HALF)
    runner, emitter = Runner(), Emitter()
    await run_adversary_round(llm, plan, runner, emitter, None, config)
    assert len(runner.ran) == 1 and runner.ran[0]["f1"] == "adv"
    prompt = [c for c in llm.calls if c.key == "reviewer:f1"][-1].messages[1]["content"]
    assert "Spec for adv" in prompt and "adv_reversed" in prompt
    assert '"dropped_rows_by":{"variant":{"control":50}}' in prompt
    assert not any(t == "option.coded" for t, _ in emitter.events)


async def test_without_smoke_config_behaviour_is_unchanged(monkeypatch: pytest.MonkeyPatch) -> None:
    llm, plan, _, _ = await prepare(monkeypatch, effects("treated", DOWN))

    async def review_proposal(llm: Any, plan: Any, emitter: Any, step: Any, option: Any) -> Any:
        return option

    monkeypatch.setattr(adversary_round, "review_proposal", review_proposal)
    runner = Runner()
    await run_adversary_round(llm, plan, runner, Emitter(), None)
    assert len(runner.ran) == 1
