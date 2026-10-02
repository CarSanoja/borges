from __future__ import annotations

from tests.armor.corpus_runner import Score, evaluate, load

OBFUSCATIONS = {"nested-base64", "url-encoding", "html-entities", "unicode-tags", "split", "bidi"}


def test_redteam_corpus_covers_the_new_techniques() -> None:
    attacks = load("attacks_redteam.json")
    assert len(attacks) >= 30
    assert {a["technique"] for a in attacks} >= OBFUSCATIONS
    assert len({a["id"] for a in attacks}) == len(attacks)


def test_every_redteam_attack_is_detected_and_no_hard_negative_is_flagged() -> None:
    score: Score = evaluate("attacks_redteam.json", "benign_redteam.json")
    print(f"recall={score.recall:.3f} false_positives={score.false_positives}")
    assert score.false_negatives == []
    assert score.false_positives == []


def test_the_original_benign_corpus_stays_clean_against_the_redteam_attacks() -> None:
    score: Score = evaluate("attacks_redteam.json", "benign.json")
    assert score.false_positives == []
