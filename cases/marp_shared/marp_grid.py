from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
from marp_options import defaults, step_order
from marp_validate import all_universes, changed_steps, run_universe

from borges.analysis.models import AnalysisResult, DecisionRule

GRID_FILE = "grid_summary.json"


def enumerate_grid(frame: pd.DataFrame, rq: int, rule: DecisionRule) -> dict:
    rows = []
    for choices in all_universes(rq):
        raw = run_universe(frame, rq, choices)
        result = AnalysisResult(
            **{k: raw[k] for k in ("estimate", "ci_low", "ci_high", "p_value", "n")}
        )
        rows.append((choices, result, rule.label(result)))
    estimates = [r.estimate for _, r, _ in rows]
    base_label = next(label for c, _, label in rows if not changed_steps(rq, c))
    flipped = [(c, r) for c, r, label in rows if label != base_label]
    by_changes: dict[int, int] = {}
    for c, _ in flipped:
        k = len(changed_steps(rq, c))
        by_changes[k] = by_changes.get(k, 0) + 1
    return {
        "rq": rq,
        "n_universes": len(rows),
        "defaults": defaults(rq),
        "steps": step_order(rq),
        "baseline_verdict": base_label,
        "n_same_verdict": len(rows) - len(flipped),
        "n_flipped": len(flipped),
        "share_same_verdict": (len(rows) - len(flipped)) / len(rows),
        "estimate_min": min(estimates),
        "estimate_max": max(estimates),
        "flipped_by_n_changes": {str(k): v for k, v in sorted(by_changes.items())},
        "single_flips": [
            {"choices": c, "estimate": r.estimate, "p_value": r.p_value}
            for c, r in flipped
            if len(changed_steps(rq, c)) == 1
        ],
    }


def write_grid(case_dir: Path, summary: dict) -> None:
    (case_dir / GRID_FILE).write_text(json.dumps(summary, indent=2) + "\n")


def read_grid(case_dir: Path) -> dict:
    return json.loads((case_dir / GRID_FILE).read_text())
