from __future__ import annotations

from pathlib import Path

import pytest

from borges.analysis import smoke_model_probe
from borges.analysis.coder import code_plan
from borges.analysis.models import AnalysisPlan, CodingSummary, Step
from borges.analysis.schemas import CoderOutput
from tests.analysis.fakes import FakeLLM, make_option, make_plan
from tests.analysis.test_coder_smoke import Recorder, config, passing_guard
from tests.analysis.test_smoke_upstream import (
    AGGREGATE,
    MODEL,
    NAMES_GROUP,
    NAMES_OUTCOME,
    NO_COVARIATES,
)

__all__ = ["passing_guard"]

GUARD = "    if ctx.get('covariates'):\n        raise KeyError('formula breaks with covariates')\n"
PICKY = MODEL.replace("    cols =", GUARD + "    cols =").replace("0.5", "0.6")
OTHER = MODEL.replace("0.5", "0.2")


def plan(aggregate_first: bool, alternatives: int = 1) -> AnalysisPlan:
    covariates = Step(
        id="c1",
        title="Covariates",
        kind="feature",
        description="Pick covariates",
        options=[
            make_option("none", True),
            *(make_option(f"alt{i}") for i in range(alternatives)),
        ],
    )
    aggregate = Step(
        id="a1",
        title="Aggregate",
        kind="transform",
        description="Aggregate",
        options=[make_option("agg", True)],
    )
    model = Step(
        id="m1",
        title="Estimator",
        kind="model",
        description="Estimate",
        options=[make_option("ols", True), make_option("cluster")],
    )
    steps = [aggregate, covariates, model] if aggregate_first else [covariates, aggregate, model]
    return make_plan().model_copy(update={"steps": steps})


def scripted(alt: str, cluster: str, alternatives: int = 1, **extra: str) -> dict[str, CoderOutput]:
    base = {
        "coder:a1.agg": AGGREGATE,
        "coder:c1.none": NO_COVARIATES,
        "coder:m1.ols": MODEL,
        "coder:m1.cluster": cluster,
        **{f"coder:c1.alt{i}": alt + f"\n# {i}" for i in range(alternatives)},
        **extra,
    }
    return {key: CoderOutput(code=code) for key, code in base.items()}


async def test_a_model_option_that_fails_only_under_an_upstream_option_is_repaired(
    tmp_path: Path,
) -> None:
    fixed = OTHER.replace("0.2", "0.4")
    llm = FakeLLM(scripted(NAMES_OUTCOME, PICKY, **{"coder:m1.cluster:smoke1": fixed}))
    recorder, summary = Recorder(), CodingSummary()
    cfg = config(tmp_path, recorder)
    coded = await code_plan(llm, plan(True), smoke=cfg, summary=summary)
    assert coded.step("m1").option("cluster").code == fixed
    assert cfg.state.outcomes["m1"][1].option.code == fixed
    content = next(c for c in llm.calls if c.key == "coder:m1.cluster:smoke1").messages[1][
        "content"
    ]
    assert "formula breaks with covariates" in content
    assert "Label alt0" in content and "Covariates" in content
    event = [e for e in recorder.events if e[1] == "cluster"][-1]
    assert event[2] == "repaired" and "caught under 'Label alt0'" in event[4]
    assert cfg.state.notes == [] and summary.failed == 0
    assert summary.repaired_after_smoke == 1


async def test_a_model_option_whose_repair_still_fails_is_dropped_and_the_default_stays(
    tmp_path: Path,
) -> None:
    llm = FakeLLM(scripted(NAMES_OUTCOME, PICKY, **{"coder:m1.cluster:smoke1": PICKY + "\n"}))
    recorder, summary = Recorder(), CodingSummary()
    cfg = config(tmp_path, recorder)
    coded = await code_plan(llm, plan(True), smoke=cfg, summary=summary)
    assert [o.id for o in coded.step("m1").options] == ["ols"]
    assert coded.step("m1").default.code == MODEL
    assert [o.option.id for o in cfg.state.outcomes["m1"]] == ["ols"]
    assert len(cfg.state.notes) == 1
    assert cfg.state.notes[0].startswith(
        "The model option 'Label cluster' was dropped: with the option 'Label alt0' of the "
        "step 'Covariates' it fails on the sample (KeyError: 'formula breaks with covariates'"
    )
    assert [e for e in recorder.events if e[1] == "cluster"][-1][2] == "failed"
    assert summary.failed == 1
    assert llm.keys().count("coder:m1.cluster:smoke1") == 1


async def test_an_alternative_two_steps_before_the_model_is_repaired(tmp_path: Path) -> None:
    llm = FakeLLM(scripted(NAMES_GROUP, OTHER, **{"coder:c1.alt0:smoke1": NAMES_OUTCOME}))
    recorder, summary = Recorder(), CodingSummary()
    cfg = config(tmp_path, recorder)
    coded = await code_plan(llm, plan(False), smoke=cfg, summary=summary)
    assert coded.step("c1").option("alt0").code == NAMES_OUTCOME
    prompt = next(c for c in llm.calls if c.key == "coder:c1.alt0:smoke1")
    assert "KeyError" in prompt.messages[1]["content"]
    event = [e for e in recorder.events if e[1] == "alt0"][-1]
    assert event[2] == "repaired" and "caught upstream" in event[4]
    assert cfg.state.notes == [] and summary.failed == 0


async def test_an_alternative_two_steps_before_the_model_is_dropped_when_unfixable(
    tmp_path: Path,
) -> None:
    llm = FakeLLM(scripted(NAMES_GROUP, OTHER, **{"coder:c1.alt0:smoke1": NAMES_GROUP + "\n"}))
    cfg = config(tmp_path, Recorder())
    summary = CodingSummary()
    coded = await code_plan(llm, plan(False), smoke=cfg, summary=summary)
    assert [o.id for o in coded.step("c1").options] == ["none"]
    assert len(cfg.state.notes) == 1 and "'Covariates' was dropped" in cfg.state.notes[0]
    assert summary.failed == 1
    assert [o.id for o in coded.step("m1").options] == ["ols", "cluster"]


async def test_no_extra_llm_call_when_everything_passes(tmp_path: Path) -> None:
    llm = FakeLLM(scripted(NAMES_OUTCOME, OTHER))
    cfg = config(tmp_path, Recorder())
    coded = await code_plan(llm, plan(False), smoke=cfg)
    assert [o.id for o in coded.step("m1").options] == ["ols", "cluster"]
    used = llm.keys()
    assert not [k for k in used if ":smoke" in k]
    assert cfg.state.notes == []


async def test_at_most_six_inputs_are_probed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[str] = []
    real = smoke_model_probe.probe_option

    async def counting(config, repair, model, option, checkpoint):
        calls.append(option.id)
        return await real(config, repair, model, option, checkpoint)

    monkeypatch.setattr(smoke_model_probe, "probe_option", counting)
    llm = FakeLLM(scripted(NAMES_OUTCOME, OTHER, alternatives=9))
    cfg = config(tmp_path, Recorder())
    await code_plan(llm, plan(False, alternatives=9), smoke=cfg)
    assert len(calls) == 12
