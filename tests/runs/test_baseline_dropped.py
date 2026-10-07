from __future__ import annotations

import io

import numpy as np
import pandas as pd

from borges.analysis.models import AnalysisPlan, Option, Step, StepTrace
from borges.garden.models import Universe
from borges.runs.baseline_dropped import located_difference
from tests.analysis.fakes import make_plan

RAW = pd.DataFrame({"WorkerID": [14, 15, 16, 17], "Vote": [1, 0, 1, 1]})


def parquet(frame: pd.DataFrame) -> bytes:
    buffer = io.BytesIO()
    frame.to_parquet(buffer)
    return buffer.getvalue()


class States:
    name = "fake"

    def __init__(self, states: dict[str, bytes]) -> None:
        self.states = states

    async def read_file(self, checkpoint, path: str) -> bytes:
        return self.states[checkpoint.id]


def plan_of(kinds: list[str]) -> AnalysisPlan:
    plan = make_plan(with_code=True)
    option = Option(id="o", label="o", rationale="r", spec="s", code="x")
    plan.steps = [
        Step(id=f"s{i}", title=f"s{i}", kind=k, description="d", options=[option])
        for i, k in enumerate(kinds)
    ]
    return plan


def chain(keys: list[str], checkpoints: list[str]) -> Universe:
    trace = StepTrace(
        step_id="m", option_id="o", rows_before=4, rows_after=2, design={"row_keys": keys}
    )
    return Universe(
        id="u",
        choices={},
        changed=[],
        kind="baseline",
        status="done",
        traces=[trace],
        checkpoints=checkpoints,
    )


async def test_the_step_after_which_the_rows_are_gone_is_named_with_their_built_values() -> None:
    """fertility_vote on 7 October, run 28: the hand-set days were wiped in the cycle-day step
    and the window filter dropped the two women."""
    built = RAW.assign(cycle_day=[9.0, np.nan, np.nan, 20.0])
    states = States(
        {"c0": parquet(built), "c1": parquet(built.iloc[[0, 3]]), "c2": parquet(built.iloc[[0, 3]])}
    )
    executor = type("E", (), {"backend": states})()
    found = await located_difference(
        executor,
        plan_of(["feature", "filter", "model"]),
        parquet(RAW),
        "WorkerID",
        chain(["14", "17"], ["c0", "c1", "c2"]),
        {"row_keys": ["14", "15", "16", "17"]},
    )
    assert found is not None
    where = found["where_the_step_by_step_code_loses_them"]
    assert where == [
        {
            "lost_after_step": "s1",
            "built_values_just_before": [
                {"WorkerID": "15", "cycle_day": "missing"},
                {"WorkerID": "16", "cycle_day": "missing"},
            ],
        }
    ]


async def test_rows_every_step_keeps_are_shown_as_the_model_received_them() -> None:
    built = RAW.assign(high=[1.0, np.nan, 0.0, 1.0])
    states = States({"c0": parquet(built), "c1": parquet(built)})
    executor = type("E", (), {"backend": states})()
    found = await located_difference(
        executor,
        plan_of(["feature", "model"]),
        parquet(RAW),
        "WorkerID",
        chain(["14", "16", "17"], ["c0", "c1"]),
        {"row_keys": ["14", "15", "16", "17"]},
    )
    assert found is not None
    assert found["where_the_step_by_step_code_loses_them"] == [
        {
            "kept_by_every_step_then_left_out_by_the_fit_of": "s1",
            "values_the_model_received": [{"WorkerID": "15", "high": "missing"}],
        }
    ]


async def test_without_a_backend_only_the_fit_difference_is_given() -> None:
    found = await located_difference(
        object(),
        plan_of(["model"]),
        parquet(RAW),
        "WorkerID",
        chain(["14"], ["c0"]),
        {"row_keys": ["14", "15"]},
    )
    assert found is not None and "where_the_step_by_step_code_loses_them" not in found
