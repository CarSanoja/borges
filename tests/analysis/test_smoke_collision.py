from __future__ import annotations

from pathlib import Path

from borges.analysis.coder import code_plan
from borges.analysis.models import CodingSummary
from borges.analysis.schemas import CoderOutput
from tests.analysis.fakes import FakeLLM, make_plan
from tests.analysis.test_coder_smoke import (
    ESTIMATE,
    KEEP,
    Recorder,
    config,
    passing_guard,
    responses,
)

__all__ = ["passing_guard"]

HEAD = "def apply(df, ctx):\n    return df.head(100).copy()"
SHIFTED = ESTIMATE.replace('"p_value": 0.5', '"p_value": 0.2')


def scripted(**overrides: str) -> dict[str, CoderOutput]:
    return responses(**{"coder:d1.trim": KEEP, "coder:m1.welch": SHIFTED, **overrides})


def prompt(llm: FakeLLM, key: str) -> str:
    return next(c for c in llm.calls if c.key == key).messages[-1]["content"]


async def test_colliding_filter_options_are_recoded_once_with_both_specs(tmp_path: Path) -> None:
    llm = FakeLLM(scripted(**{"coder:d1.trim:collision": HEAD, "coder:d1.keep:collision": KEEP}))
    recorder, summary = Recorder(), CodingSummary()
    cfg = config(tmp_path, recorder)
    coded = await code_plan(llm, make_plan(), smoke=cfg, summary=summary)
    step = coded.step("d1")
    assert step.option("trim").code == HEAD
    assert step.option("keep").code == KEEP
    text = prompt(llm, "coder:d1.trim:collision")
    assert "Spec for trim on outcome" in text and "Spec for keep on outcome" in text
    assert "same output although the specs differ" in text
    assert "implement exactly its own spec" in text
    assert llm.keys().count("coder:d1.trim:collision") == 1
    note = next(e[4] for e in recorder.events if e[1] == "trim" and e[3] == 2)
    assert "output collision with keep" in note
    assert summary.options_recoded_by_output_check == 1
    assert cfg.state.notes == []


async def test_a_collision_that_persists_is_kept_and_noted(tmp_path: Path) -> None:
    llm = FakeLLM(scripted(**{"coder:d1.trim:collision": KEEP, "coder:d1.keep:collision": KEEP}))
    cfg = config(tmp_path, Recorder())
    coded = await code_plan(llm, make_plan(), smoke=cfg)
    assert [o.id for o in coded.step("d1").options] == ["keep", "trim"]
    assert len(cfg.state.notes) == 1
    note = cfg.state.notes[0]
    assert "d1.trim" in note and "identical output" in note


async def test_a_model_collision_compares_estimate_interval_p_value_and_n(tmp_path: Path) -> None:
    llm = FakeLLM(scripted(**{"coder:m1.welch": ESTIMATE, "coder:m1.welch:collision": SHIFTED}))
    coded = await code_plan(llm, make_plan(), smoke=config(tmp_path, Recorder()))
    model = coded.step("m1")
    assert model.option("welch").code == SHIFTED
    assert model.option("ols").code == ESTIMATE


async def test_distinct_outputs_cost_no_recode(tmp_path: Path) -> None:
    llm = FakeLLM(scripted(**{"coder:d1.trim": HEAD, "coder:m1.welch": SHIFTED}))
    await code_plan(llm, make_plan(), smoke=config(tmp_path, Recorder()))
    used = llm.keys()
    assert not [k for k in used if k.endswith(":collision") or k.endswith(":scale")]


async def test_identical_specs_are_not_a_collision(tmp_path: Path) -> None:
    plan = make_plan()
    plan.step("d1").option("trim").spec = plan.step("d1").option("keep").spec
    llm = FakeLLM(scripted())
    await code_plan(llm, plan, smoke=config(tmp_path, Recorder()))
    used = llm.keys()
    assert "coder:d1.trim:collision" not in used
