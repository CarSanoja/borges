from __future__ import annotations

import pytest

from borges.bench.blade_rules import RULES
from borges.bench.blade_source import (
    BladeNotFound,
    annotated_ids,
    load_dataset,
    resolve_root,
)
from tests.bench.support import MINI

REAL_ANNOTATED = {
    "affairs",
    "amtl",
    "boxes",
    "caschools",
    "crofoot",
    "fish",
    "hurricane",
    "mortgage",
    "panda_nuts",
    "reading",
    "soccer",
    "teachingratings",
}


def test_missing_blade_directory_explains_how_to_get_it(monkeypatch) -> None:
    monkeypatch.delenv("BORGES_BLADE_DIR", raising=False)
    with pytest.raises(BladeNotFound, match="github.com/behavioral-data/BLADE"):
        resolve_root(None)


def test_environment_variable_is_used(monkeypatch) -> None:
    monkeypatch.setenv("BORGES_BLADE_DIR", str(MINI))
    assert resolve_root(None) == MINI


def test_annotated_datasets_are_listed() -> None:
    assert annotated_ids(resolve_root(MINI)) == ["hurricane", "teachingratings"]


def test_hurricane_expert_decisions_are_parsed() -> None:
    dataset = load_dataset(resolve_root(MINI), "hurricane")
    assert dataset.num_rows == 94
    assert "IV: feminity metric of hurricane name" in dataset.items("cvar")
    assert len(dataset.items("cvar")) == 4
    models = dataset.items("model")
    assert "negative binomial regression" in models and len(models) == 3
    assert any("Katrina" in text for text in dataset.items("transform"))
    assert all("ROOT" not in text for text in dataset.items("transform"))
    assert dataset.columns["alldeaths"].startswith("Total number of deaths")


def test_moderators_keep_their_blade_wording() -> None:
    dataset = load_dataset(resolve_root(MINI), "teachingratings")
    assert "Moderator: gender interacting with beauty variable" in dataset.items("cvar")


def test_every_annotated_blade_dataset_has_a_rule_and_nothing_else_does() -> None:
    assert set(RULES) == REAL_ANNOTATED


def test_rules_are_explicit_and_signed() -> None:
    for dataset_id, rule in RULES.items():
        decision = rule.decision_rule()
        assert decision.alpha == 0.05 and decision.threshold == 0.0, dataset_id
        assert "0 means no effect" in decision.metric
        assert rule.iv and rule.dv and rule.direction and rule.question.endswith("?")


def test_readme_documents_every_rule_and_the_hand_written_table() -> None:
    from pathlib import Path

    readme = (Path(__file__).parents[2] / "src" / "borges" / "bench" / "README.md").read_text()
    for dataset_id in RULES:
        assert f"| {dataset_id} |" in readme
    assert "written by hand" in readme and "info.json" in readme
