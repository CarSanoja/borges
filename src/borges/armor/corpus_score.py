from __future__ import annotations

import threading
import time
from typing import Any

from borges.armor.corpus_eval import evaluate, flagged, load
from borges.armor.fresh_score import fresh_score

SUITES = (
    ("attacks", "attacks.json", "benign.json"),
    ("redteam", "attacks_redteam.json", "benign_redteam.json"),
)
HELD_OUT_FILE = "heldout.json"
SOURCE = "armor/corpus/*.json screened by the running server's own patterns"
_LOCK = threading.Lock()
_CACHED: dict[str, Any] | None = None


def compute_score() -> dict[str, Any]:
    suites: list[dict[str, Any]] = []
    techniques: set[str] = set()
    for name, attacks_file, benign_file in SUITES:
        attacks = load(attacks_file)
        techniques |= {a["technique"] for a in attacks if a.get("technique") != "plain"}
        score = evaluate(attacks_file, benign_file)
        suites.append(
            {
                "name": name,
                "attacks": len(attacks),
                "detected": score.true_positives,
                "benign": score.benign_total,
                "false_positives": len(score.false_positives),
            }
        )
    held = load(HELD_OUT_FILE)
    caught = [h["id"] for h in held if flagged(h)]
    fresh = fresh_score()
    return {
        "suites": suites,
        "attacks": sum(s["attacks"] for s in suites),
        "detected": sum(s["detected"] for s in suites),
        "benign": sum(s["benign"] for s in suites),
        "false_positives": sum(s["false_positives"] for s in suites),
        "obfuscations": sorted(techniques),
        "held_out": {
            "paraphrases": len(held),
            "caught": len(caught),
            "known_misses": sorted(h["id"] for h in held if h["id"] not in caught),
        },
        "fresh_held_out": {
            "set": fresh["set"],
            "date": fresh["date"],
            "attacks": fresh["attacks"],
            "caught": fresh["caught"],
            "benign": fresh["benign"],
            "false_positives": fresh["false_positives"],
            "routed_to_second_stage": fresh["routed_to_second_stage"]["misses_routed"],
        },
        "computed_at": time.time(),
        "source": SOURCE,
    }


def armor_score(refresh: bool = False) -> dict[str, Any]:
    global _CACHED
    with _LOCK:
        if _CACHED is None or refresh:
            _CACHED = compute_score()
        return _CACHED
