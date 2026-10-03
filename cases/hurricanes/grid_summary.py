from __future__ import annotations

import json
import warnings

import pandas as pd
from option_code import BASE_OPTIONS
from prepare import CASE_DIR
from reference import FACTS
from validation import STEP_ORDER, all_universes, load_codes, run_universe


def planner_options() -> dict[str, list[str]]:
    options: dict[str, list[str]] = {step: [] for step in STEP_ORDER}
    for key in BASE_OPTIONS:
        step, option_id = key.split(".", 1)
        options[step].append(option_id)
    return options


def main() -> None:
    warnings.filterwarnings("ignore")
    frame = pd.read_parquet(CASE_DIR / "data.parquet")
    codes = load_codes()
    rows = []
    for choices in all_universes(planner_options()):
        try:
            raw = run_universe(frame, choices, codes)
        except (ValueError, KeyError, ArithmeticError):
            continue
        rows.append({"estimate": raw["estimate"], "p_value": raw["p_value"]})
    grid = pd.DataFrame(rows)
    significant = (grid["estimate"] > 0) & (grid["p_value"] < 0.05)
    summary = {
        "specifications": int(len(grid)),
        "significant_predicted_direction": int(significant.sum()),
        "share_significant": float(significant.mean()),
        "median_estimate": float(grid["estimate"].median()),
        "min_estimate": float(grid["estimate"].min()),
        "max_estimate": float(grid["estimate"].max()),
        "share_positive": float((grid["estimate"] > 0).mean()),
        "reference_simonsohn_2020": {
            "specifications": FACTS["specifications"],
            "significant_predicted_direction": FACTS["significant_predicted_direction"],
            "median_estimate": FACTS["median_effect_additional_deaths"],
        },
    }
    (CASE_DIR / "grid_summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
