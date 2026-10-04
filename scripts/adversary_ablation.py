"""Ablate the adversary on recorded live runs.

For every completed run JSON in the given directories, compare the planner-only arm (the explored
universes that use no adversary option) with the full garden, and pair every universe holding one
adversary option with its twin that has the planner's default at that step. A verdict change
counts as adversary-only when the twin keeps the original verdict.

Usage: uv run python scripts/adversary_ablation.py DIR [DIR ...] [--json OUT]
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any


def _origins(plan: dict[str, Any]) -> tuple[dict[str, str], dict[str, str], dict[str, str]]:
    origin: dict[str, str] = {}
    label: dict[str, str] = {}
    default: dict[str, str] = {}
    for step in plan.get("steps", []):
        for option in step.get("options", []):
            origin[option["id"]] = option.get("origin") or "planner"
            label[option["id"]] = option.get("label") or option["id"]
            if option.get("is_default"):
                default[step["id"]] = option["id"]
    return origin, label, default


def _key(choices: dict[str, str]) -> tuple[tuple[str, str], ...]:
    return tuple(sorted(choices.items()))


def ablate_run(run: dict[str, Any]) -> dict[str, Any] | None:
    if run.get("status") != "completed" or not run.get("plan") or not run.get("garden"):
        return None
    origin, label, default = _origins(run["plan"])
    universes = [u for u in run["garden"]["universes"].values() if u.get("status") == "done"]
    by_choices = {_key(u["choices"]): u for u in universes}
    adversarial = [o for o, v in origin.items() if v == "adversary"]

    def uses_adversary(universe: dict[str, Any]) -> list[str]:
        return [c for c in universe["choices"].values() if c in adversarial]

    planner_only = [u for u in universes if not uses_adversary(u)]
    with_adversary = [u for u in universes if uses_adversary(u)]
    alone: list[dict[str, str]] = []
    for universe in with_adversary:
        used = uses_adversary(universe)
        if len(used) != 1 or not universe.get("flipped"):
            continue
        step = next(s for s, c in universe["choices"].items() if c == used[0])
        twin = by_choices.get(_key({**universe["choices"], step: default.get(step, "")}))
        if twin is not None and not twin.get("flipped"):
            alone.append(
                {"step": step, "option": label[used[0]], "verdict": str(universe.get("verdict"))}
            )
    return {
        "run_id": run.get("run_id"),
        "case": run.get("case_id"),
        "verdict": run.get("report", {}).get("verdict") if run.get("report") else None,
        "adversary_options": len(adversarial),
        "universes": len(universes),
        "planner_only_universes": len(planner_only),
        "planner_only_flips": sum(1 for u in planner_only if u.get("flipped")),
        "adversary_universes": len(with_adversary),
        "adversary_flips": sum(1 for u in with_adversary if u.get("flipped")),
        "adversary_alone": alone,
    }


def summarise(rows: list[dict[str, Any]]) -> dict[str, Any]:
    cases: dict[str, dict[str, Any]] = defaultdict(lambda: defaultdict(int))
    for row in rows:
        case = cases[row["case"]]
        case["runs"] += 1
        case["runs_with_adversary_options"] += int(row["adversary_options"] > 0)
        case["planner_only_finds_a_flip"] += int(row["planner_only_flips"] > 0)
        case["full_finds_a_flip"] += int(row["planner_only_flips"] + row["adversary_flips"] > 0)
        case["only_the_adversary_finds_a_flip"] += int(
            row["planner_only_flips"] == 0 and row["adversary_flips"] > 0
        )
        case["runs_with_an_adversary_alone_flip"] += int(bool(row["adversary_alone"]))
    return {name: dict(values) for name, values in sorted(cases.items())}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("dirs", nargs="+", type=Path)
    parser.add_argument("--json", type=Path)
    args = parser.parse_args()
    rows = []
    for directory in args.dirs:
        for path in sorted(directory.glob("*.json")):
            try:
                run = json.loads(path.read_text())
            except ValueError:
                continue
            row = ablate_run(run) if isinstance(run, dict) else None
            if row is not None:
                rows.append({**row, "file": path.name})
    summary = summarise(rows)
    for name, values in summary.items():
        print(name, values)
    for row in rows:
        for flip in row["adversary_alone"]:
            print(f"  {row['file']}: {flip['option']} ({flip['step']}) -> {flip['verdict']}")
    if args.json is not None:
        args.json.write_text(json.dumps({"summary": summary, "runs": rows}, indent=2))


if __name__ == "__main__":
    main()
