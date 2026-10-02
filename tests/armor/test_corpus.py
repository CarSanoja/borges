from __future__ import annotations

from tests.armor.corpus_runner import Score, evaluate, load

MIN_ATTACKS = 40
MIN_BENIGN = 40
OBFUSCATIONS = {"homoglyph", "zero-width", "base64", "split", "hex", "rot13", "reversed"}


def test_corpus_is_large_and_covers_the_obfuscations() -> None:
    attacks, benign = load("attacks.json"), load("benign.json")
    assert len(attacks) >= MIN_ATTACKS and len(benign) >= MIN_BENIGN
    assert {a["technique"] for a in attacks} >= OBFUSCATIONS
    spanish = [a for a in attacks if "ignora" in str(a.get("text", "")).lower()]
    assert spanish
    assert len({a["id"] for a in attacks}) == len(attacks)


def test_benign_texts_come_from_the_real_cases() -> None:
    benign = load("benign.json")
    real = [b for b in benign if b["source"] != "synthetic"]
    assert len(real) >= MIN_BENIGN
    assert {b["source"] for b in real} >= {
        "checkout_ab",
        "red_cards",
        "marp_norms",
        "marp_religiosity",
        "bank_marketing_calls",
    }


def test_every_attack_is_detected_and_no_benign_text_is_flagged() -> None:
    score: Score = evaluate()
    attacks = len(load("attacks.json"))
    print(
        f"recall={score.recall:.3f} ({score.true_positives}/{attacks}) "
        f"precision={score.precision:.3f} false_positives={len(score.false_positives)}"
        f"/{score.benign_total}"
    )
    assert score.false_negatives == []
    assert score.false_positives == []
    assert score.recall == 1.0 and score.precision == 1.0
