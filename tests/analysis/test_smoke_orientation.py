from __future__ import annotations

import io

import numpy as np
import pandas as pd
import pytest

from borges.analysis import coder
from borges.analysis.coder import code_plan
from borges.analysis.coder_smoke import SmokeConfig
from borges.analysis.models import AnalysisPlan, CodingSummary, DecisionRule, Option, Step
from borges.analysis.schemas import CoderOutput
from borges.analysis.smoke_orientation import orientation_error, probe_correlation
from tests.analysis.fakes import FakeLLM, make_option, make_profile
from tests.analysis.smoke_fakes import ScriptBackend, effects

N = 60
UP = [float(i % 2) for i in range(N)]
DOWN = [1.0 - v for v in UP]
RAMP = [float(i) for i in range(N)]


def test_treatment_against_control_indicator_is_reversed() -> None:
    error = orientation_error(["x"], effects("x", UP), effects("x", DOWN))
    assert error is not None and "column 'x' is reversed relative to the default option" in error
    assert "-1.00" in error and "never swap groups or reverse a coding" in error


@pytest.mark.parametrize(
    ("default", "other"),
    [
        (RAMP, [3 * v + 1 for v in RAMP]),
        ([float(i % 5) for i in range(N)], [float((i + 0) % 5 >= 3) for i in range(N)]),
        (RAMP, [v / 7 for v in RAMP]),
    ],
)
def test_same_direction_columns_pass(default: list[float], other: list[float]) -> None:
    r = probe_correlation(effects("x", default), effects("x", other), "x")
    assert r is not None and r > 0.5
    assert orientation_error(["x"], effects("x", default), effects("x", other)) is None


def test_rater_skin_tone_scales_pass() -> None:
    rng = np.random.default_rng(1)
    rater1 = list(rng.integers(1, 6, size=N).astype(float))
    rater2 = [float(np.clip(v + rng.integers(-1, 2), 1, 5)) for v in rater1]
    assert orientation_error(["tone"], effects("tone", rater1), effects("tone", rater2)) is None


def test_median_split_against_fixed_threshold_passes() -> None:
    rng = np.random.default_rng(2)
    base = list(rng.normal(size=N))
    median = float(np.median(base))
    split = [float(v > median) for v in base]
    fixed = [float(v > 0.3) for v in base]
    assert orientation_error(["hi"], effects("hi", split), effects("hi", fixed)) is None


def test_pca_against_mean_passes_once_oriented_and_fails_flipped() -> None:
    rng = np.random.default_rng(3)
    mean_score = list(rng.normal(size=N))
    pca = [0.8 * v + 0.1 * float(rng.normal()) for v in mean_score]
    flipped = [-v for v in pca]
    default = effects("score", mean_score)
    assert orientation_error(["score"], default, effects("score", pca)) is None
    assert orientation_error(["score"], default, effects("score", flipped)) is not None


def test_too_few_shared_pairs_is_not_judged() -> None:
    short = effects("x", UP[:20])
    assert orientation_error(["x"], short, effects("x", DOWN[:20])) is None


def test_constant_column_is_not_judged() -> None:
    assert orientation_error(["x"], effects("x", [1.0] * N), effects("x", DOWN)) is None


def test_missing_effects_are_not_judged() -> None:
    assert orientation_error(["x"], None, effects("x", UP)) is None
    assert orientation_error(["x"], effects("x", UP), None) is None


TREAT = "def apply(df, ctx):\n    treat_variant = 1\n    return df"
CONTROL = "def apply(df, ctx):\n    control_variant = 1\n    return df"
CONTROL_FIXED = "def apply(df, ctx):\n    control_fixed = 1\n    return df"
ESTIMATE = "def estimate(df, ctx):\n    model_marker = 1\n    return {}"


def feature_plan(produces: list[str]) -> AnalysisPlan:
    options = [make_option("treat", True), make_option("control")]
    return AnalysisPlan(
        question="Does the treatment raise the outcome?",
        estimand="Mean difference in outcome between groups",
        decision_rule=DecisionRule(metric="mean_diff"),
        dataset=make_profile(),
        steps=[
            Step(
                id="f1",
                title="Indicator",
                kind="feature",
                description="Code the group",
                options=options,
                produces=produces,
            ),
            Step(
                id="m1",
                title="Estimator",
                kind="model",
                description="Estimate",
                options=[Option(**{**make_option("ols", True).model_dump(), "code": None})],
            ),
        ],
    )


def data_bytes() -> bytes:
    frame = pd.DataFrame({"group": ["a", "b"] * 150, "outcome": np.arange(300, dtype=float)})
    buffer = io.BytesIO()
    frame.to_parquet(buffer)
    return buffer.getvalue()


@pytest.fixture(autouse=True)
def passing_guard(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(coder, "check_code", lambda code, kind: [])


class Recorder:
    def __init__(self) -> None:
        self.events: list[tuple] = []

    async def __call__(self, *args) -> None:
        self.events.append(args)


def responses(**overrides: str) -> dict[str, CoderOutput]:
    base = {"coder:f1.treat": TREAT, "coder:f1.control": CONTROL, "coder:m1.ols": ESTIMATE}
    return {k: CoderOutput(code=v) for k, v in {**base, **overrides}.items()}


def script() -> list[tuple[str, dict | None]]:
    return [
        ("treat_variant", effects("treated", UP)),
        ("control_variant", effects("treated", DOWN)),
        ("control_fixed", effects("treated", UP)),
    ]


async def test_reversed_option_is_repaired_through_the_smoke_loop() -> None:
    llm = FakeLLM(responses(**{"coder:f1.control:smoke1": CONTROL_FIXED}))
    recorder, summary = Recorder(), CodingSummary()
    backend = ScriptBackend(script())
    config = SmokeConfig(backend, data_bytes(), recorder)
    plan = feature_plan(["treated"])
    coded = await code_plan(llm, plan, smoke=config, summary=summary)
    assert coded.step("f1").option("control").code == CONTROL_FIXED
    prompt = next(c for c in llm.calls if c.key == "coder:f1.control:smoke1").messages[1]["content"]
    assert "column 'treated' is reversed relative to the default option" in prompt
    assert [e[2] for e in recorder.events if e[1] == "control"] == ["passed", "repaired"]
    assert summary.repaired_after_smoke == 1 and summary.failed == 0


async def test_still_reversed_after_repairs_is_dropped() -> None:
    llm = FakeLLM(
        responses(
            **{
                "coder:f1.control:smoke1": CONTROL,
                "coder:f1.control:smoke2": CONTROL,
            }
        )
    )
    recorder, summary = Recorder(), CodingSummary()
    config = SmokeConfig(ScriptBackend(script()), data_bytes(), recorder)
    coded = await code_plan(llm, feature_plan(["treated"]), smoke=config, summary=summary)
    assert [o.id for o in coded.step("f1").options] == ["treat"]
    last = [e for e in recorder.events if e[1] == "control"][-1]
    assert last[2] == "failed" and "is reversed relative to the default" in last[4]
    assert summary.failed == 1


async def test_without_produces_the_columns_added_by_the_default_are_used() -> None:
    llm = FakeLLM(responses(**{"coder:f1.control:smoke1": CONTROL_FIXED}))
    config = SmokeConfig(ScriptBackend(script()), data_bytes(), Recorder())
    coded = await code_plan(llm, feature_plan([]), smoke=config)
    assert coded.step("f1").option("control").code == CONTROL_FIXED


async def test_aligned_options_cost_no_extra_calls() -> None:
    aligned = [
        ("treat_variant", effects("treated", UP)),
        ("control_variant", effects("treated", [v * 2 for v in UP])),
    ]
    llm = FakeLLM(responses())
    config = SmokeConfig(ScriptBackend(aligned), data_bytes(), Recorder())
    await code_plan(llm, feature_plan(["treated"]), smoke=config)
    assert not any("smoke" in key for key in [c.key for c in llm.calls])
