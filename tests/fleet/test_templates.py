from __future__ import annotations

from borges.cases.registry import CaseRegistry
from borges.config import Settings
from borges.fleet.templates import analysis_templates


def test_cases_become_templates(settings: Settings) -> None:
    templates = analysis_templates(CaseRegistry(settings.borges_cases_dir))
    by_id = {t.id: t for t in templates}
    assert {"checkout_ab", "red_cards", "marp_norms", "marp_religiosity"} <= set(by_id)
    checkout = by_id["checkout_ab"]
    assert checkout.owner == "borges-core" and checkout.metric.startswith("conversion lift")
    assert checkout.decision_rule["positive_label"] == "SHIP"
