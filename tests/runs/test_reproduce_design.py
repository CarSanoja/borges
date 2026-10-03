from __future__ import annotations

from borges.runs.reproduce import Reproduction, reproduction_lines
from tests.garden.synthetic import option, plan_of, result, step_of, trace, universe


def plan():
    return plan_of(
        step_of("rows", "filter", option("keep", True), option("drop")),
        step_of("model", "model", option("m", True), option("n")),
    )


def lines_for(design: dict[str, object] | None) -> list[str]:
    p = plan()
    traces = [trace("model", **design)] if design else []
    recorded = universe(p, {"rows": "drop"}, result(0.5), traces=[])
    rerun = universe(p, {"rows": "drop"}, result(0.5), traces=traces)
    rep = Reproduction(recorded.id, recorded, rerun, None, None, [])
    return reproduction_lines("demo", p, rep)


def test_a_rank_deficient_rerun_prints_match_and_a_warning() -> None:
    lines = lines_for({"deficient": True, "rank": 12, "columns": 13})
    assert any(line.startswith("MATCH") for line in lines)
    warning = lines[-1]
    assert warning.startswith("WARNING") and "rank 12 of 13 columns" in warning
    assert "predates the design check" in warning


def test_a_full_rank_rerun_prints_no_warning() -> None:
    lines = lines_for({"deficient": False, "rank": 13, "columns": 13})
    assert lines[-1].startswith("MATCH")


def test_a_rerun_without_a_design_record_prints_no_warning() -> None:
    assert lines_for(None)[-1].startswith("MATCH")
