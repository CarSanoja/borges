from __future__ import annotations

import json
from pathlib import Path

import pytest

from borges.cases.registry import CaseRegistry
from tests.runs.fakes import parquet_bytes, write_case


@pytest.fixture
def cases_dir(tmp_path: Path) -> Path:
    write_case(tmp_path, "alpha", with_recording=True)
    write_case(tmp_path, "beta")
    (tmp_path / "no_case_json").mkdir()
    (tmp_path / "no_case_json" / "data.parquet").write_bytes(b"x")
    return tmp_path


def test_list_returns_cards_sorted_and_ignores_folders_without_case_json(cases_dir: Path) -> None:
    cards = CaseRegistry(cases_dir).list()
    assert [c.id for c in cards] == ["alpha", "beta"]
    alpha = cards[0]
    assert alpha.n_rows == 3 and alpha.has_recording is True
    assert cards[1].has_recording is False
    assert alpha.title == "Demo case" and alpha.decision_rule.metric == "diff"


def test_get_and_unknown_ids(cases_dir: Path) -> None:
    registry = CaseRegistry(cases_dir)
    assert registry.get("alpha").dataset_name == "demo data"
    for bad in ("missing", "no_case_json", "../alpha", ""):
        with pytest.raises(KeyError):
            registry.get(bad)


def test_data_fixtures_and_recording(cases_dir: Path) -> None:
    registry = CaseRegistry(cases_dir)
    assert registry.data_bytes("alpha") == parquet_bytes()
    assert registry.fixtures_dir("alpha") == cases_dir / "alpha" / "fixtures"
    recording = registry.recording("alpha")
    assert recording is not None and recording[0].type == "stage"
    assert registry.recording("beta") is None
    with pytest.raises(KeyError):
        registry.data_bytes("missing")


def test_missing_cases_dir_lists_nothing(tmp_path: Path) -> None:
    assert CaseRegistry(tmp_path / "none").list() == []


def test_card_matches_listing(cases_dir: Path) -> None:
    registry = CaseRegistry(cases_dir)
    assert registry.card("alpha") == registry.list()[0]
    with pytest.raises(KeyError):
        registry.card("nope")


@pytest.mark.parametrize("case_id", ["checkout_ab", "red_cards"])
def test_shipped_cases_load(case_id: str) -> None:
    registry = CaseRegistry(Path(__file__).resolve().parents[2] / "cases")
    card = registry.card(case_id)
    assert card.n_rows > 0
    assert registry.fixtures_dir(case_id).is_dir()
    assert registry.data_bytes(case_id)


def _write_live_only(cases_dir: Path, case_id: str) -> None:
    write_case(cases_dir, case_id)
    spec_path = cases_dir / case_id / "case.json"
    spec = json.loads(spec_path.read_text())
    spec["live_only"] = True
    spec_path.write_text(json.dumps(spec))
    (cases_dir / case_id / "fixtures").rmdir()


def test_live_only_flag_defaults_false_and_is_reported(cases_dir: Path) -> None:
    _write_live_only(cases_dir, "gamma")
    registry = CaseRegistry(cases_dir)
    cards = {c.id: c for c in registry.list()}
    assert cards["alpha"].live_only is False
    assert cards["gamma"].live_only is True and cards["gamma"].has_recording is False
    assert registry.card("gamma").model_dump()["live_only"] is True


def test_scripted_run_of_live_only_case_is_refused_with_a_clear_message(cases_dir: Path) -> None:
    _write_live_only(cases_dir, "gamma")
    registry = CaseRegistry(cases_dir)
    assert registry.fixtures_dir("gamma") is None
    with pytest.raises(ValueError, match="live-only.*llm=nebius"):
        registry.require_scripted("gamma")
    registry.require_scripted("alpha")
    assert registry.fixtures_dir("alpha") is not None
