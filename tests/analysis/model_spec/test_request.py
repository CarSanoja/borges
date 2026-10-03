from __future__ import annotations

import json

import pytest

from borges.analysis import coder
from borges.analysis.code_guard import check_code
from borges.analysis.coder import code_plan, generate_checked
from borges.analysis.model_spec import request as request_module
from borges.analysis.model_spec.request import request_template, template_family
from borges.analysis.models import AnalysisPlan, ColumnProfile, DatasetProfile
from borges.analysis.schemas import CoderOutput
from borges.llm.client import LLMError, Role
from borges.llm.scripted_provider import ScriptedLLM
from tests.analysis.fakes import FakeLLM, make_plan

FREE = (
    "def estimate(df, ctx):\n"
    '    m = float(df["outcome"].mean())\n'
    '    return {"estimate": m, "ci_low": m - 1.0, "ci_high": m + 1.0, "p_value": 0.5, "n": 1}'
)
KEEP = "def apply(df, ctx):\n    return df"
GOOD_SPEC = {
    "supported": True,
    "family": "ols",
    "outcome": "outcome",
    "exposure": "score",
    "cov_type": "HC3",
}
KEY = "coder:m1.welch:spec"
FREE_KEY = "coder:m1.welch"


def plan_with_score() -> AnalysisPlan:
    plan = make_plan()
    columns = [
        *plan.dataset.columns,
        ColumnProfile(name="score", dtype="float64", n_missing=0, n_unique=50),
    ]
    plan.dataset = DatasetProfile(name="trial", n_rows=100, columns=columns)
    return plan


def llm_with(spec: dict | None) -> FakeLLM:
    responses: dict = {FREE_KEY: CoderOutput(code=FREE)}
    if spec is not None:
        responses[KEY] = spec
    return FakeLLM(responses)


async def code_welch(llm: FakeLLM, plan: AnalysisPlan | None = None, models=None):
    plan = plan or plan_with_score()
    step = plan.step("m1")
    return await generate_checked(llm, plan, step, step.option("welch"), models)


async def test_valid_spec_becomes_the_option_code_with_a_note() -> None:
    llm = llm_with(GOOD_SPEC)
    models: list[str] = []
    code, attempts, note = await code_welch(llm, models=models)
    assert attempts == 1 and note == "template: ols"
    assert "sm.OLS" in code and 'cov_type="HC3"' in code
    assert llm.keys() == [KEY]
    call = llm.calls[0]
    assert call.role is Role.CODER and call.schema.__name__ == "ModelSpecOutput"
    assert models == ["fake"]


async def test_template_family_reads_the_note() -> None:
    assert template_family("template: negbin") == "negbin"
    assert template_family(None) is None
    assert template_family("removed a stray closing-bracket line at the end of the code") is None


@pytest.mark.parametrize(
    "spec",
    [
        {"supported": False, "reason": "needs a mixed model"},
        {**GOOD_SPEC, "exposure": "ghost"},
        {**GOOD_SPEC, "report": "odds_ratio"},
        {**GOOD_SPEC, "family": "gee"},
        {"supported": True},
    ],
)
async def test_unsupported_or_invalid_spec_falls_back_to_free_code(spec: dict) -> None:
    llm = llm_with(spec)
    code, attempts, note = await code_welch(llm)
    assert code == FREE and attempts == 1 and note is None
    assert llm.keys() == [KEY, FREE_KEY]


async def test_missing_spec_falls_back_to_free_code() -> None:
    llm = llm_with(None)
    code, attempts, note = await code_welch(llm)
    assert code == FREE and attempts == 1 and note is None
    assert llm.keys() == [FREE_KEY] and llm.declined_specs == [KEY]


async def test_guard_failing_template_falls_back(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[str] = []

    def reject(code: str, kind: str, intent: str = "") -> list[str]:
        seen.append(code)
        return ["denied"] if "sm.OLS" in code else []

    monkeypatch.setattr(request_module, "check_code", reject)
    monkeypatch.setattr(coder, "check_code", check_code)
    llm = llm_with(GOOD_SPEC)
    code, _, note = await code_welch(llm)
    assert code == FREE and note is None and len(seen) == 1


async def test_guard_is_called_with_the_option_intent(monkeypatch: pytest.MonkeyPatch) -> None:
    intents: list[str] = []

    def record(code: str, kind: str, intent: str = "") -> list[str]:
        intents.append(f"{kind}|{intent}")
        return []

    monkeypatch.setattr(request_module, "check_code", record)
    assert await request_template(llm_with(GOOD_SPEC), plan_with_score(), *_welch()) is not None
    assert intents == ["model|Label welch Spec for welch on outcome"]


def _welch():
    plan = plan_with_score()
    step = plan.step("m1")
    return step, step.option("welch")


async def test_only_model_steps_ask_for_a_spec() -> None:
    llm = FakeLLM({"coder:d1.trim": CoderOutput(code=KEEP), KEY: GOOD_SPEC})
    plan = plan_with_score()
    step = plan.step("d1")
    code, _, note = await generate_checked(llm, plan, step, step.option("trim"))
    assert code == KEEP and note is None and llm.keys() == ["coder:d1.trim"]


async def test_code_plan_reports_the_template_note() -> None:
    plan = plan_with_score()
    plan.step("d1").options = [plan.step("d1").option("keep")]
    plan.step("d1").option("keep").code = "def apply(df, ctx):\n    return df"
    plan.step("m1").options = [plan.step("m1").option("welch")]
    plan.step("m1").option("welch").is_default = True
    events: list[tuple] = []

    async def on_coded(*args) -> None:
        events.append(args)

    coded = await code_plan(llm_with(GOOD_SPEC), plan, on_coded=on_coded)
    assert "sm.OLS" in coded.step("m1").option("welch").code
    assert events == [("m1", "welch", True, 1, "template: ols", ["fake"])]


async def test_scripted_runs_have_no_spec_fixtures_and_fall_back(tmp_path) -> None:
    (tmp_path / "coder__m1.welch.json").write_text(json.dumps({"parsed": {"code": FREE}}))
    plan = plan_with_score()
    step = plan.step("m1")
    llm = ScriptedLLM(tmp_path)
    with pytest.raises(LLMError):
        await llm.complete(Role.CODER, [], key=KEY)
    code, attempts, note = await generate_checked(llm, plan, step, step.option("welch"))
    assert code == FREE and attempts == 1 and note is None
