from __future__ import annotations

import pytest

from borges.armor.corpus_eval import flagged, load

HELD_OUT = load("heldout.json")
CAUGHT = [h for h in HELD_OUT if h["status"] == "caught"]
MISSED = [h for h in HELD_OUT if h["status"] == "missed"]


def test_the_held_out_set_has_both_caught_and_missed_paraphrases() -> None:
    assert len(CAUGHT) >= 5 and len(MISSED) >= 3
    assert len({h["id"] for h in HELD_OUT}) == len(HELD_OUT)


@pytest.mark.parametrize("entry", CAUGHT, ids=lambda e: e["id"])
def test_paraphrases_the_jury_found_are_now_caught_by_the_semantic_family(entry: dict) -> None:
    assert flagged(entry), entry["text"]


@pytest.mark.parametrize("entry", MISSED, ids=lambda e: e["id"])
def test_known_misses_are_still_misses_so_the_limit_stays_documented(entry: dict) -> None:
    assert not flagged(entry), (
        f"{entry['id']} is now caught: set its status to 'caught' in armor/corpus/heldout.json"
    )
