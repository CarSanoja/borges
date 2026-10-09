"""Armor on the blind set of 7 October 2026, written by a model with no access to the code.

The patterns are re-run on every text, so the deterministic figure is always the running
screen's. The judge's verdicts come from the one recorded measurement (171 calls on Nemotron
Ultra): production sends a text to the judge only when its field is reviewed and the text is
ambiguous, so the second-stage figure is the patterns or the recorded verdict on those texts.
"""

from __future__ import annotations

import json
from typing import Any

from borges.armor.ambiguity import is_ambiguous
from borges.armor.corpus_eval import CORPUS, flagged, load
from borges.armor.fresh_score import FRESH_FILE, to_entry

BLIND_FILE = "blind_2026-10-07.json"
RESULTS_FILE = "blind_2026-10-07_results.json"
SET_NAME = "blind"
SET_DATE = "2026-10-07"


def recorded_results() -> dict[str, Any]:
    return json.loads((CORPUS / RESULTS_FILE).read_text(encoding="utf-8"))


def blind_rows() -> list[dict[str, Any]]:
    verdicts = {row["id"]: row for row in recorded_results()["rows"]}
    rows = []
    for raw in load(BLIND_FILE):
        verdict = verdicts[raw["id"]]
        patterns = flagged(to_entry(raw))
        judged = verdict["new"] and verdict["reviewed"] and is_ambiguous(raw["text"])
        rows.append(
            {
                "id": raw["id"],
                "label": raw["label"],
                "field": raw["field"],
                "patterns": patterns,
                "recorded_patterns": verdict["det"],
                "with_second_stage": patterns or judged,
            }
        )
    return rows


def blind_score() -> dict[str, Any]:
    rows = blind_rows()
    attacks = [r for r in rows if r["label"] == "attack"]
    benign = [r for r in rows if r["label"] == "benign"]
    results = recorded_results()
    return {
        "set": SET_NAME,
        "file": BLIND_FILE,
        "date": SET_DATE,
        "attacks": len(attacks),
        "benign": len(benign),
        "caught": sum(r["patterns"] for r in attacks),
        "false_positives": sum(r["patterns"] for r in benign),
        "second_stage_caught": sum(r["with_second_stage"] for r in attacks),
        "second_stage_false_positives": sum(r["with_second_stage"] for r in benign),
        "judge_measured_at": results["measured_at_utc"],
        "judge_calls": results["calls"],
    }


def blind_claims(score: dict[str, Any], quote: str = "`") -> list[str]:
    blind = score["blind_held_out"]
    fresh = score["fresh_held_out"]
    return [
        f"{quote}{blind['file']}{quote} (7 October)",
        f"{blind['caught']} of {blind['attacks']} attacks caught by the patterns",
        f"{blind['second_stage_caught']} with the judge-model second stage",
        f"{blind['second_stage_false_positives']} of {blind['benign']} benign texts flagged",
        f"{quote}{FRESH_FILE}{quote} (4 October)",
        f"{fresh['caught']} of {fresh['attacks']} attacks caught by the patterns",
        f"{fresh['false_positives']} of {fresh['benign']} benign texts flagged",
    ]


def blind_sentence(score: dict[str, Any], quote: str = "") -> str:
    claims = blind_claims(score, quote)
    return (
        "On two blind sets, written by writers who never saw the screen: "
        f"{claims[0]}, {claims[1]} and {claims[2]}, {claims[3]}; "
        f"{claims[4]}, {claims[5]}, {claims[6]}."
    )
