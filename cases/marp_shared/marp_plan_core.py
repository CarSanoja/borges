from __future__ import annotations

CITATION = "Hoogeveen, Sarafoglou et al. (2022), Religion, Brain & Behavior"


def opt(oid, label, rationale, spec, source, default=False):
    return {
        "id": oid,
        "label": label,
        "rationale": rationale,
        "spec": spec,
        "is_default": default,
        "source": f"{CITATION}: {source}",
    }
