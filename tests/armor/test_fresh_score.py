from __future__ import annotations

from borges.armor.fresh_score import fresh_score

SCORE = fresh_score()


def test_the_fresh_set_has_seventy_attacks_and_seventy_benign() -> None:
    assert SCORE["attacks"] == 70
    assert SCORE["benign"] == 70


def test_counts_are_consistent() -> None:
    assert SCORE["caught"] + len(SCORE["missed"]) == SCORE["attacks"]
    assert SCORE["false_positives"] == len(SCORE["false_positive_ids"])
    assert sum(v["total"] for v in SCORE["per_field"].values()) == SCORE["attacks"]
    assert sum(v["total"] for v in SCORE["per_technique"].values()) == SCORE["attacks"]
    assert sum(v["caught"] for v in SCORE["per_technique"].values()) == SCORE["caught"]
    assert sum(v["total"] for v in SCORE["benign_per_field"].values()) == SCORE["benign"]
    assert SCORE["routed_to_second_stage"]["misses_routed"] <= len(SCORE["missed"])
