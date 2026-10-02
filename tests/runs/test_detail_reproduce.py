from __future__ import annotations

from borges.analysis.models import AnalysisPlan, DatasetProfile, DecisionRule, Option, Step
from borges.garden.models import Flip, Garden, Universe
from borges.runs.detail import build_universe_detail
from borges.runs.export_script import build_script
from borges.runs.models import RunSnapshot


def _snapshot(reproduce_command: str | None) -> RunSnapshot:
    step = Step(
        id="s1",
        title="Model",
        kind="model",
        description="d",
        options=[
            Option(
                id="a",
                label="A",
                rationale="r",
                spec="s",
                is_default=True,
                code="def estimate(df, ctx):\n    return {}\n",
            )
        ],
    )
    rule = DecisionRule(metric="m")
    plan = AnalysisPlan(
        question="q",
        estimand="e",
        decision_rule=rule,
        dataset=DatasetProfile(name="d", n_rows=1, columns=[]),
        steps=[step],
    )
    universe = Universe(id="u1", choices={"s1": "a"}, changed=[], kind="baseline", status="done")
    garden = Garden(universes={"u1": universe}, baseline_id="u1")
    flip = None
    if reproduce_command:
        flip = Flip.model_construct(universe_id="u1", reproduce_command=reproduce_command)
    return RunSnapshot(run_id="r9", plan=plan, garden=garden, flip=flip, question="q")


def test_command_ignores_any_stored_reproduce_command() -> None:
    detail = build_universe_detail(_snapshot("python steps/gone.py"), "u1")
    assert "steps/" not in detail.reproduce_command
    assert detail.reproduce_command == "python borges_r9_u1.py --data path/to/data.parquet"
    assert detail.reproduce_kind == "script"
    assert detail.script_url == "/api/runs/r9/universes/u1/script"


def test_recorded_run_gets_the_borges_reproduce_command() -> None:
    detail = build_universe_detail(_snapshot(None), "u1", recorded_case="checkout_ab")
    assert detail.reproduce_command == "uv run borges reproduce --case checkout_ab --universe u1"
    assert detail.reproduce_kind == "case"


def test_exported_script_embeds_the_step_code_and_takes_a_data_path() -> None:
    script = build_script(_snapshot(None), "u1", "borges_r9_u1.py")
    compile(script, "borges_r9_u1.py", "exec")
    assert "def estimate(df, ctx)" in script
    assert "--data" in script
    assert "python borges_r9_u1.py --data path/to/data.parquet" in script
