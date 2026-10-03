from __future__ import annotations

import json

import pytest

from borges.analysis.narrative_flip import flip_sentence, has_sentence, problems
from borges.cases.registry import CaseRegistry
from borges.runs.state import fold
from tests.cases.marp_support import CASES_DIR

SCRIPTED_FLIP_CASES = ["checkout_ab", "red_cards", "marp_norms"]


@pytest.mark.parametrize("case_id", SCRIPTED_FLIP_CASES)
def test_scripted_narrator_fixture_already_carries_the_flip_sentence(case_id: str) -> None:
    registry = CaseRegistry(CASES_DIR)
    events = registry.recording(case_id)
    assert events
    snapshot = fold(events)
    assert snapshot.plan is not None and snapshot.report is not None
    fixture = json.loads((CASES_DIR / case_id / "fixtures" / "narrator.json").read_text())
    narrative = fixture["parsed"]["narrative"]
    sentence = flip_sentence(snapshot.plan, snapshot.report)
    assert sentence is not None
    assert has_sentence(narrative, sentence)
    assert problems(snapshot.plan, snapshot.report, narrative) == []
    assert json.loads(fixture["text"])["narrative"] == narrative
