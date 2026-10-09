from __future__ import annotations

import json
from pathlib import Path

import pytest

from borges.evaluation.calibration_grid import smoke_cells
from borges.evaluation.calibration_study import result_document, run_study

pytestmark = pytest.mark.timeout(600)


def test_smoke_study_runs_two_datasets_from_the_data(tmp_path: Path) -> None:
    cells = smoke_cells()
    rows, scanned = run_study(cells, tmp_path / "rows.jsonl", workers=1)
    assert len(rows) == 2
    by_cell = {r["cell"]: r for r in rows}
    planted = by_cell["null|artefact|all"]
    clean = by_cell["large|clean|all"]
    assert planted["baseline_estimate"] != clean["baseline_estimate"]
    assert planted["universes"] >= 3 and clean["universes"] >= 3
    assert clean["original_verdict"] == "SHIP"
    assert planted["flip_found"] is True and "internal_traffic" in planted["flip_steps"]
    document = result_document(rows, scanned, cells)
    assert set(document["summary"]) == set(by_cell)
    json.dumps(document)
    resumed, _ = run_study(cells, tmp_path / "rows.jsonl", workers=1)
    assert len(resumed) == 2
