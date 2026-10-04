from __future__ import annotations

from collections import Counter
from typing import Any

from borges.armor.ambiguity import is_ambiguous
from borges.armor.corpus_eval import flagged, load

FRESH_FILE = "fresh_2026-10-04.json"
SET_NAME = "fresh"
SET_DATE = "2026-10-04"


def to_entry(raw: dict[str, Any]) -> dict[str, Any]:
    if raw["field"] == "column_note":
        return {"field": "column_notes", "texts": {"c": raw["text"]}}
    return {"field": raw["field"], "text": raw["text"]}


def _by(rows: list[dict[str, Any]], key: str) -> dict[str, dict[str, int]]:
    totals: dict[str, dict[str, int]] = {}
    for row in rows:
        slot = totals.setdefault(row[key], {"total": 0, "caught": 0})
        slot["total"] += 1
        slot["caught"] += int(row["flagged"])
    return dict(sorted(totals.items()))


def fresh_score() -> dict[str, Any]:
    rows = []
    for raw in load(FRESH_FILE):
        rows.append(
            {
                **raw,
                "flagged": flagged(to_entry(raw)),
                "ambiguous": is_ambiguous(raw["text"]),
            }
        )
    attacks = [r for r in rows if r["label"] == "attack"]
    benign = [r for r in rows if r["label"] == "benign"]
    missed = [r for r in attacks if not r["flagged"]]
    false_positives = [r for r in benign if r["flagged"]]
    routed = Counter()
    for r in rows:
        kind = "benign" if r["label"] == "benign" else ("caught" if r["flagged"] else "missed")
        routed[kind] += int(r["ambiguous"])
    return {
        "set": SET_NAME,
        "date": SET_DATE,
        "attacks": len(attacks),
        "caught": len(attacks) - len(missed),
        "benign": len(benign),
        "false_positives": len(false_positives),
        "recall": (len(attacks) - len(missed)) / len(attacks) if attacks else 1.0,
        "false_positive_rate": len(false_positives) / len(benign) if benign else 0.0,
        "per_field": _by(attacks, "field"),
        "per_technique": _by(attacks, "technique"),
        "benign_per_field": _by(benign, "field"),
        "missed": [
            {"id": r["id"], "technique": r["technique"], "field": r["field"]} for r in missed
        ],
        "false_positive_ids": [r["id"] for r in false_positives],
        "routed_to_second_stage": {
            "missed_attacks": routed["missed"],
            "caught_attacks": routed["caught"],
            "benign": routed["benign"],
            "misses_routed": routed["missed"],
        },
    }
