from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from borges.cases.registry import CaseRegistry

CASES = Path(__file__).resolve().parents[2] / "cases"
CASE_ID = "bank_marketing_calls"


@pytest.fixture(scope="module")
def registry() -> CaseRegistry:
    return CaseRegistry(CASES)


def test_card_is_live_only_with_a_live_recording_and_no_scripted_one(
    registry: CaseRegistry,
) -> None:
    card = registry.card(CASE_ID)
    assert card.live_only is True
    assert card.has_scripted_recording is False
    assert card.has_live_recording is (CASES / CASE_ID / "recorded-live" / "events.jsonl").is_file()
    assert card.has_recording is card.has_live_recording
    assert card.n_rows == 45211
    assert card.decision_rule.comparator.value == "lt"
    assert registry.recording(CASE_ID) is None


def test_no_fixtures_or_recording_on_disk() -> None:
    assert not (CASES / CASE_ID / "fixtures").exists()
    assert not (CASES / CASE_ID / "recorded").exists()


def test_scripted_run_is_refused_and_fixtures_absent(registry: CaseRegistry) -> None:
    assert registry.fixtures_dir(CASE_ID) is None
    with pytest.raises(ValueError, match="live-only"):
        registry.require_scripted(CASE_ID)


def test_data_matches_the_uci_dataset_shape() -> None:
    frame = pd.read_parquet(CASES / CASE_ID / "data.parquet")
    assert frame.shape == (45211, 17)
    assert set(frame["y"].unique()) == {0, 1}
    assert round(frame["y"].mean(), 4) == 0.117
    assert frame["campaign"].max() == 63


def test_license_and_source_are_documented() -> None:
    readme = (CASES / CASE_ID / "README.md").read_text(encoding="utf-8")
    assert "CC BY 4.0" in readme
    assert "10.24432/C5K306" in readme
    spec = json.loads((CASES / CASE_ID / "case.json").read_text(encoding="utf-8"))
    assert spec["live_only"] is True and spec["reference"] == []
