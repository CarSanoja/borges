"""Tabulate the committed live recordings as Markdown.

For every case with cases/<case>/recorded-live/, the first table gives the run, model calls,
tokens, cost and universes from recording.json and the last usage event; the second gives the
original verdict, the smallest flip found and the two universes to reproduce: the baseline and
the flip, or, without a flip, the finished universe farthest from the baseline. Universes can
report on different scales (log deaths, raw deaths), so farthest means the largest change in z,
where z = (estimate - decision threshold) / standard error, the standard error read from the
95% interval. A ratio measure (positive estimate and bounds, positive threshold) uses logs.

Usage: uv run python scripts/live_runs_table.py [CASES_DIR]
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path
from typing import Any

Z95 = 1.959964
FARTHEST_MEASURE = (
    "the largest change in z = (estimate - decision threshold) / standard error, the standard "
    "error read from the 95% interval (on the log scale for a ratio measure), which does not "
    "depend on the scale a universe reports in"
)


def _events(folder: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in (folder / "events.jsonl").read_text().splitlines()]


def _result(r: dict[str, Any]) -> str:
    return (
        f"{r['estimate']:.4g} [{r['ci_low']:.4g}, {r['ci_high']:.4g}], p {r['p_value']:.3g}, "
        f"n {r['n']}"
    )


def _universes(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [e["data"]["universe"] for e in events if e["type"] == "universe.finished"]


def z_score(result: dict[str, Any], threshold: float) -> float:
    estimate, low, high = result["estimate"], result["ci_low"], result["ci_high"]
    if threshold > 0 and min(estimate, low, high) > 0:
        estimate, low, high, threshold = (math.log(v) for v in (estimate, low, high, threshold))
    error = (high - low) / (2 * Z95)
    return (estimate - threshold) / error if error > 0 else 0.0


def _farthest(
    universes: list[dict[str, Any]], baseline: dict[str, Any], threshold: float = 0.0
) -> dict[str, Any] | None:
    done = [u for u in universes if u["status"] == "done" and u["id"] != baseline["id"]]
    origin = z_score(baseline["result"], threshold)
    return max(done, key=lambda u: abs(z_score(u["result"], threshold) - origin), default=None)


def _threshold(events: list[dict[str, Any]]) -> float:
    started = [e["data"] for e in events if e["type"] == "run.started"]
    rule = started[-1].get("decision_rule") if started else None
    return float((rule or {}).get("threshold", 0.0))


def load(folder: Path) -> dict[str, Any]:
    events = _events(folder)
    recording = json.loads((folder / "recording.json").read_text())
    usage = [e["data"] for e in events if e["type"] == "usage"][-1]
    report = [e["data"]["report"] for e in events if e["type"] == "report.ready"][-1]
    universes = _universes(events)
    baseline = next(u for u in universes if not u["changed"])
    flip = report.get("minimal_flip")
    other = (
        flip["universe_id"]
        if flip
        else (_farthest(universes, baseline, _threshold(events)) or {}).get("id")
    )
    return {
        "case": recording["case_id"],
        "recording": recording,
        "usage": usage,
        "report": report,
        "failed": sum(u["status"] != "done" for u in universes),
        "ids": [baseline["id"], *([other] if other else [])],
    }


def _flip(report: dict[str, Any]) -> str:
    flip = report.get("minimal_flip")
    if not flip:
        return "none"
    labels = " plus ".join(c["to_label"] for c in flip["changes"])
    return f"{labels}: {_result(flip['flipped_result'])}, {flip['flipped_verdict']}"


def render(rows: list[dict[str, Any]]) -> str:
    lines = [
        "| Case | Run | Commit | Calls (cached) | Tokens in / out | Cost | Universes (failed) |",
        "|---|---|---|---|---|---|---|",
    ]
    for r in rows:
        u, rec = r["usage"], r["recording"]
        lines.append(
            f"| {r['case']} | {rec['run_id']} | `{rec['commit']}` | {u['llm_calls']} "
            f"({u['cached_calls']}) | {u['tokens_in']:,} / {u['tokens_out']:,} | "
            f"${u['cost_usd']:.4f} | {r['report']['n_universes']} ({r['failed']}) |"
        )
    lines += [
        "",
        "| Case | Original verdict | Smallest flip found | Universes to reproduce |",
        "|---|---|---|---|",
    ]
    for r in rows:
        report = r["report"]
        original = f"{report['original_verdict']}: {_result(report['original_result'])}"
        ids = ", ".join(f"`{i}`" for i in r["ids"])
        lines.append(f"| {r['case']} | {original} | {_flip(report)} | {ids} |")
    lines += [
        "",
        f"Without a flip, the second id is the finished universe with {FARTHEST_MEASURE}.",
    ]
    return "\n".join(lines) + "\n"


def main() -> None:
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("cases")
    folders = sorted(p for p in root.glob("*/recorded-live") if (p / "recording.json").exists())
    print(render([load(f) for f in folders]), end="")


if __name__ == "__main__":
    main()
