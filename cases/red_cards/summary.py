from __future__ import annotations

from typing import Any

import pandas as pd
from validation import STEP_ORDER, all_universes, changed_steps, run_universe

from borges.analysis.models import AnalysisResult, DecisionRule

PLANNER_OPTIONS = {
    "skin_tone": ["mean_raters", "rater1_only", "rater2_only", "extremes_only"],
    "exclusions": ["rated_only", "rated_frequent_refs"],
    "covariates": ["none", "physique", "full"],
    "model": ["binomial_glm", "poisson_offset", "binomial_cluster"],
}
ACCEPTED_ADVERSARY = {"covariates": "adv_full_plus_bias"}
REJECTED_ADVERSARY = {"exclusions": "adv_low_iat_referees_only"}


def with_extra(options: dict[str, list[str]], extra: dict[str, str]) -> dict[str, list[str]]:
    return {s: [*ids, *([extra[s]] if s in extra else [])] for s, ids in options.items()}


def summarize(frame: pd.DataFrame, codes: dict[str, str], rule: DecisionRule) -> dict[str, Any]:
    options = with_extra(with_extra(PLANNER_OPTIONS, ACCEPTED_ADVERSARY), REJECTED_ADVERSARY)
    rows = []
    for choices in all_universes(options):
        raw = run_universe(frame, choices, codes)
        result = AnalysisResult(
            **{k: raw[k] for k in ("estimate", "ci_low", "ci_high", "p_value", "n")}
        )
        rows.append(
            {
                "choices": choices,
                "changes": len(changed_steps(choices)),
                "result": result,
                "label": rule.label(result),
                "rejected": REJECTED_ADVERSARY["exclusions"] in choices.values(),
            }
        )
    usable = [r for r in rows if not r["rejected"]]
    base = next(r for r in rows if r["changes"] == 0)
    singles = [r for r in usable if r["changes"] == 1]
    return {
        "baseline": base,
        "singles": singles,
        "rejected_single": next(r for r in rows if r["rejected"] and r["changes"] == 1),
        "flipped": [r for r in usable if r["label"] != base["label"]],
        "estimates": [r["result"].estimate for r in usable],
        "steps": STEP_ORDER,
        "rows": rows,
    }
