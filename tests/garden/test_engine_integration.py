from __future__ import annotations

import io
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pytest

from borges.analysis.code_guard import check_code
from borges.analysis.models import (
    AnalysisPlan,
    DatasetProfile,
    DecisionRule,
    Option,
    Step,
)
from borges.garden.executor import GardenExecutor
from borges.garden.models import Garden
from borges.garden.search import minimal_flip, single_flip_choices
from borges.garden.verify import verify_flip
from borges.runs.events import CheckpointCreatedData
from borges.sandbox.local_backend import LocalBackend

KEEP_ALL = "def apply(df, ctx):\n    return df\n"

EXCLUDE_INTERNAL = (
    "def apply(df, ctx):\n"
    "    ctx['internal_excluded'] = True\n"
    "    return df[~df['is_internal']].reset_index(drop=True)\n"
)

PLATFORM_ALL = "def apply(df, ctx):\n    return df\n"

PLATFORM_WEB = (
    "def apply(df, ctx):\n    return df[df['platform'] == 'web'].reset_index(drop=True)\n"
)

DIFF_PROPS = """
import math

from scipy import stats


def estimate(df, ctx):
    a = df[df['variant'] == 'A']['converted']
    b = df[df['variant'] == 'B']['converted']
    pa, pb = a.mean(), b.mean()
    se = math.sqrt(pa * (1 - pa) / len(a) + pb * (1 - pb) / len(b))
    diff = (pb - pa) * 100
    half = 1.959964 * se * 100
    p_value = 2 * (1 - stats.norm.cdf(abs(pb - pa) / se))
    return {
        'estimate': float(diff),
        'ci_low': float(diff - half),
        'ci_high': float(diff + half),
        'p_value': float(p_value),
        'n': int(len(df)),
    }
"""

LOGIT = """
import numpy as np
import statsmodels.api as sm


def estimate(df, ctx):
    x = sm.add_constant((df['variant'] == 'B').astype(float).to_numpy())
    fit = sm.Logit(df['converted'].astype(float).to_numpy(), x).fit(disp=0)
    low, high = fit.conf_int()[1]
    return {
        'estimate': float(fit.params[1]),
        'ci_low': float(low),
        'ci_high': float(high),
        'p_value': float(fit.pvalues[1]),
        'n': int(len(df)),
    }
"""


def make_frame() -> pd.DataFrame:
    rng = np.random.default_rng(7)
    n = 4000
    variant = np.array(["A", "B"] * (n // 2))
    internal = (variant == "B") & (rng.random(n) < 0.2)
    rate = np.where(internal, 0.35, 0.10)
    return pd.DataFrame(
        {
            "variant": variant,
            "converted": (rng.random(n) < rate).astype(int),
            "is_internal": internal,
            "platform": rng.choice(["web", "ios", "android"], size=n),
        }
    )


def option(oid: str, code: str, default: bool = False) -> Option:
    return Option(
        id=oid,
        label=oid.replace("_", " "),
        rationale=f"because {oid}",
        spec=oid,
        is_default=default,
        defensibility=None if default else 0.9,
        source=None if default else "docs",
        code=code,
    )


def make_plan(frame: pd.DataFrame) -> AnalysisPlan:
    return AnalysisPlan(
        question="Does variant B increase conversion?",
        estimand="difference in conversion rate, percentage points",
        decision_rule=DecisionRule(metric="diff_pp", threshold=0.0),
        dataset=DatasetProfile(name="synthetic", n_rows=len(frame), columns=[]),
        steps=[
            Step(
                id="internal",
                title="Internal traffic",
                kind="filter",
                description="Treatment of internal users",
                options=[
                    option("keep_all", KEEP_ALL, True),
                    option("exclude_internal", EXCLUDE_INTERNAL),
                ],
            ),
            Step(
                id="platform",
                title="Platform",
                kind="filter",
                description="Which platforms to include",
                options=[
                    option("all", PLATFORM_ALL, True),
                    option("web_only", PLATFORM_WEB),
                ],
            ),
            Step(
                id="model",
                title="Estimator",
                kind="model",
                description="How the effect is estimated",
                options=[
                    option("diff_props", DIFF_PROPS, True),
                    option("logit", LOGIT),
                ],
            ),
        ],
    )


class Recorder:
    def __init__(self) -> None:
        self.events: list[tuple[str, dict[str, Any]]] = []

    async def __call__(self, event_type: str, data: dict[str, Any]) -> None:
        self.events.append((event_type, data))

    def of(self, event_type: str) -> list[dict[str, Any]]:
        return [d for t, d in self.events if t == event_type]


def test_every_option_passes_the_code_guard() -> None:
    plan = make_plan(make_frame())
    for step in plan.steps:
        for opt in step.options:
            assert opt.code is not None
            assert check_code(opt.code, step.kind) == [], (step.id, opt.id)


async def test_engine_end_to_end(tmp_path: Path) -> None:
    frame = make_frame()
    plan = make_plan(frame)
    buffer = io.BytesIO()
    frame.to_parquet(buffer)
    data = buffer.getvalue()
    recorder = Recorder()
    backend = LocalBackend(tmp_path)
    executor = GardenExecutor(backend, plan, data, emit=recorder, concurrency=3)
    await executor.setup()

    baseline = await executor.run_universe(plan.default_choices(), "baseline")
    assert baseline.status == "done", baseline.error
    assert baseline.result is not None
    assert baseline.result.estimate > 0
    assert baseline.verdict == "SHIP"
    assert baseline.result.n == len(frame)

    garden = Garden(baseline_id=baseline.id)
    garden.add(baseline)
    singles = [
        await executor.run_universe(choices, "single") for choices in single_flip_choices(plan)
    ]
    assert len(singles) == 3
    for universe in singles:
        assert universe.status == "done", universe.error
        garden.add(universe)

    by_changed = {u.changed[0]: u for u in singles}
    internal = by_changed["internal"]
    assert internal.choices["internal"] == "exclude_internal"
    assert internal.flipped is True
    assert internal.verdict == "DON'T SHIP"
    assert internal.result is not None and internal.result.n < len(frame)
    assert by_changed["model"].result is not None

    flip = minimal_flip(plan, garden)
    assert flip is not None
    assert flip.universe_id == internal.id
    assert [c.step_id for c in flip.changes] == ["internal"]

    verified = await verify_flip(backend, plan, data, flip, garden)
    assert verified.reproduced is True
    assert verified.reproduce_command

    path_lengths = sum(len(u.checkpoints) for u in [baseline, *singles])
    assert executor.checkpoints_created - 1 < path_lengths
    assert path_lengths == 12

    created = [CheckpointCreatedData.model_validate(d) for d in recorder.of("checkpoint.created")]
    assert len(created) == executor.checkpoints_created
    root = created[0]
    assert (root.parent_id, root.step_id, root.option_id, root.depth) == (None, None, None, 0)
    known = {c.checkpoint_id for c in created}
    for item in created[1:]:
        assert item.parent_id in known
        assert item.step_id is not None and item.option_id is not None
        assert 1 <= item.depth <= len(plan.steps)

    started = recorder.of("universe.started")
    finished = recorder.of("universe.finished")
    assert len(started) == len(finished) == 4
    assert all(set(d) == {"universe"} for d in started + finished)
    assert {d["universe"]["id"] for d in finished} == set(garden.universes)
    assert all(d["universe"]["status"] == "done" for d in finished)
    assert all(d["universe"]["status"] == "running" for d in started)
    assert {t for t, _ in recorder.events} == {
        "checkpoint.created",
        "universe.started",
        "universe.finished",
    }
    await backend.close()


@pytest.mark.parametrize("seed_rows", [4000])
def test_frame_is_the_documented_size(seed_rows: int) -> None:
    frame = make_frame()
    assert len(frame) == seed_rows
    assert frame.loc[frame["is_internal"], "variant"].eq("B").all()
