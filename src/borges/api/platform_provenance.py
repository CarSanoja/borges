from __future__ import annotations

from typing import Any

LIVE = {
    "kind": "live",
    "source": "computed by the running server when this response was built",
}

MEASURED_ARMOR = {
    "facts.measured.jury_heldout_before_semantic_family": {
        "kind": "measured",
        "value": "0 of 5 held-out result-steering paraphrases detected",
        "date": "2026-10-03",
        "source": "r6 jury probe of the injection screen; armor/corpus/heldout.json",
    },
}


def _armor(computed_at: float | None, source: str | None) -> dict[str, Any]:
    corpus = {
        "kind": "live",
        "source": f"{source or 'armor corpus'}; computed once at server start and cached",
        "computed_at": computed_at,
    }
    return {"facts.corpus": corpus, **MEASURED_ARMOR}


def provenance(pillar_id: str, facts: dict[str, Any]) -> dict[str, Any]:
    overrides: dict[str, Any] = {}
    if pillar_id == "armor":
        corpus = facts.get("corpus") or {}
        overrides = _armor(corpus.get("computed_at"), corpus.get("source"))
    return {"default": LIVE, "overrides": overrides}
