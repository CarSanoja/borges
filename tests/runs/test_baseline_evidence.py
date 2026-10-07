from __future__ import annotations

import io

import pandas as pd

from borges.analysis.models import StepTrace
from borges.garden.models import Universe
from borges.runs.baseline_evidence import fit_difference

RAW = pd.DataFrame({"WorkerID": [14, 15, 16, 17], "Vote": [1, 0, 1, 1], "Sure1": [9, 2, 3, 8]})


def data() -> bytes:
    buffer = io.BytesIO()
    RAW.to_parquet(buffer)
    return buffer.getvalue()


def ours(keys: list[str] | None, means: dict[str, float]) -> Universe:
    design = {"means": means, **({"row_keys": keys} if keys is not None else {})}
    trace = StepTrace(step_id="m", option_id="o", rows_before=2, rows_after=2, design=design)
    return Universe(id="u", choices={}, changed=[], kind="baseline", status="done", traces=[trace])


def test_the_rows_the_reference_fits_and_the_step_code_drops_are_named_with_raw_values() -> None:
    """fertility_vote on 7 October, runs 25 and 26: 301 women against the reference's 303."""
    theirs = {"row_keys": ["14", "15", "16", "17"], "means": {"high": 0.48}}
    found = fit_difference(data(), "WorkerID", ours(["14", "17"], {"high": 0.0}), theirs)
    assert found is not None
    assert found["n_only_in_reference"] == 2 and found["n_only_in_step_by_step"] == 0
    assert [r["WorkerID"] for r in found["rows_only_in_reference"]] == ["15", "16"]
    assert found["design_means"] == {"step_by_step": {"high": 0.0}, "reference": {"high": 0.48}}


def test_without_row_keys_only_the_design_means_are_given() -> None:
    found = fit_difference(data(), "WorkerID", ours(None, {"x": 1.0}), {"means": {"x": -1.0}})
    assert found == {"design_means": {"step_by_step": {"x": 1.0}, "reference": {"x": -1.0}}}


def test_nothing_to_compare_gives_nothing() -> None:
    assert fit_difference(None, None, ours(None, {}), {}) is None
