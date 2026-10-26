from __future__ import annotations

from pathlib import Path

from borges.analysis.profile import profile_dataframe
from borges.cases.registry import CaseRegistry
from borges.memory.case_labels import curated_labels, with_case_labels
from borges.memory.signatures import dataset_fingerprint
from borges.runs.pipeline_data import load_dataframe

CASES = Path(__file__).resolve().parents[2] / "cases"


def fingerprint_of(case_id: str) -> str:
    frame = load_dataframe(CaseRegistry(CASES).data_bytes(case_id))
    return dataset_fingerprint(profile_dataframe(frame, case_id))


def test_a_curated_fingerprint_is_shown_with_its_case_title() -> None:
    fp = fingerprint_of("checkout_ab")
    summary = {"datasets": [{"dataset": fp, "code": 1}, {"dataset": "e" * 64, "code": 2}]}
    labelled = with_case_labels(summary, CASES)
    title = CaseRegistry(CASES).get("checkout_ab").title
    assert [row["label"] for row in labelled["datasets"]] == [title, None]
    assert labelled["datasets"][0]["code"] == 1


def test_an_empty_memory_is_returned_without_reading_the_cases(tmp_path: Path) -> None:
    curated_labels.cache_clear()
    summary = {"datasets": []}
    assert with_case_labels(summary, tmp_path / "missing") is summary
    assert curated_labels.cache_info().misses == 0
    assert curated_labels(str(tmp_path / "missing")) == {}
