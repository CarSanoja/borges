from __future__ import annotations

from pathlib import Path

import pandas as pd

from borges.bench.blade_adapter import SAMPLE_SEED, build_case, to_request
from borges.bench.blade_source import load_dataset, resolve_root
from borges.cases.models import CaseSpec
from borges.cases.registry import CaseRegistry
from tests.bench.support import MINI


def dataset(name: str):
    return load_dataset(resolve_root(MINI), name)


def test_case_is_a_valid_borges_case(tmp_path: Path) -> None:
    adapted = build_case(dataset("hurricane"), tmp_path, max_rows=1000, max_universes=24)
    spec = CaseSpec.model_validate_json((adapted.case_dir / "case.json").read_text())
    assert spec.id == "blade_hurricane"
    assert spec.question == "Do hurricanes with more feminine names cause more deaths?"
    assert spec.decision_rule.comparator.value == "gt" and spec.max_universes == 24
    assert spec.column_notes["alldeaths"].startswith("Total number of deaths")
    assert adapted.n_rows == 94 and adapted.note is None
    card = CaseRegistry(tmp_path).card("blade_hurricane")
    assert card.n_rows == 94


def test_large_datasets_are_sampled_with_a_note(tmp_path: Path) -> None:
    adapted = build_case(dataset("hurricane"), tmp_path, max_rows=40, max_universes=10)
    assert adapted.n_rows == 40 and adapted.source_rows == 94
    assert adapted.note == f"sampled 40 of 94 rows (seed {SAMPLE_SEED}) to bound sandbox time"
    again = build_case(dataset("hurricane"), tmp_path / "b", max_rows=40, max_universes=10)
    first = pd.read_parquet(adapted.case_dir / "data.parquet")
    second = pd.read_parquet(again.case_dir / "data.parquet")
    assert first.equals(second)


def test_request_points_at_the_case(tmp_path: Path) -> None:
    adapted = build_case(dataset("teachingratings"), tmp_path, max_rows=1000, max_universes=12)
    request = to_request(adapted, "scripted", 12)
    assert (request.case_id, request.llm, request.backend, request.max_universes) == (
        "blade_teachingratings",
        "scripted",
        "local",
        12,
    )
