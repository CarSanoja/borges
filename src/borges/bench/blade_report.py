from __future__ import annotations

import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path

from borges.bench.blade_metrics import KINDS, mean_f1
from borges.bench.blade_prompts import ATTRIBUTION
from borges.bench.blade_suite import ArmResult, BenchResult
from borges.config import REPO_ROOT

METHOD = (
    "Borges explores universes (one analysis path each); every distinct universe is converted "
    "to BLADE's submission format (conceptual variables read off the executed code, transform "
    "code, model code). Matching follows BLADE: conceptual variables count as matched at "
    "similarity 8 or more; coverage is the share of expert decisions matched by any universe "
    "(for models the denominator is the smaller of the expert models and the analyses, because "
    "one analysis fits one model); hit rate is the mean share of a universe's decisions that "
    "match an expert decision. A kind whose matcher reply is unavailable is reported as missing, "
    "never as 0%. "
    "Transforms are matched semantically by the matcher, not by BLADE's data-value hashes, and "
    "BLADE's model-with-variables metric is not computed."
)


def git_commit() -> str | None:
    try:
        done = subprocess.run(
            ["git", "-C", str(REPO_ROOT), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            timeout=10,
            check=True,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return done.stdout.strip() or None


def arm_row(arm: ArmResult) -> dict:
    row = {
        "dataset": arm.dataset,
        "arm": arm.arm,
        "analyses": len(arm.analyses),
        "universes_run": arm.universes,
        "run_cost_usd": round(arm.run_cost_usd, 5),
        "matcher_cost_usd": round(arm.matcher_cost_usd, 5),
        "run_ids": arm.run_ids,
        "errors": arm.errors,
    }
    if arm.metrics:
        row["metrics"] = {
            k: {x: v for x, v in arm.metrics[k].items() if x != "pairs"} for k in KINDS
        }
        row["pairs"] = {k: arm.metrics[k].get("pairs", []) for k in KINDS}
        score = mean_f1(arm.metrics)
        row["mean_f1"] = None if score is None else round(score, 4)
    return row


def summary_dict(result: BenchResult, matcher_name: str) -> dict:
    config = result.config
    return {
        "generated_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "commit": git_commit(),
        "llm": config.llm,
        "matcher": matcher_name,
        "arms": config.arms,
        "repeats": config.repeats,
        "max_universes": config.max_universes,
        "max_rows": config.max_rows,
        "estimated_cost_usd": result.estimate_usd,
        "total_cost_usd": round(result.total_cost, 5),
        "aborted": result.aborted,
        "skipped": result.skipped,
        "notes": result.notes,
        "method": METHOD,
        "attribution": ATTRIBUTION,
        "rows": [arm_row(arm) for arm in result.arms],
    }


def _pct(value: float) -> str:
    return f"{100 * value:.0f}%"


def _cells(metrics: dict) -> str:
    if "missing" in metrics:
        return "missing | missing"
    return f"{_pct(metrics['coverage'])} | {_pct(metrics['hit_rate'])}"


def markdown(summary: dict) -> str:
    lines = [
        "# BLADE benchmark summary",
        "",
        f"LLM `{summary['llm']}`, matcher `{summary['matcher']}`, repeats {summary['repeats']}, "
        f"commit `{summary['commit']}`, total cost ${summary['total_cost_usd']:.4f}.",
        "",
        "| dataset | arm | analyses | cvar cov | cvar hit | model cov | model hit | "
        "transform cov | transform hit | mean F1 | cost USD |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in summary["rows"]:
        cost = row["run_cost_usd"] + row["matcher_cost_usd"]
        if "metrics" not in row:
            lines.append(
                f"| {row['dataset']} | {row['arm']} | 0 | - | - | - | - | - | - | - | {cost:.4f} |"
            )
            continue
        m = row["metrics"]
        cells = " | ".join(_cells(m[k]) for k in ("cvar", "model", "transform"))
        score = "-" if row["mean_f1"] is None else f"{row['mean_f1']:.2f}"
        lines.append(
            f"| {row['dataset']} | {row['arm']} | {row['analyses']} | {cells} | "
            f"{score} | {cost:.4f} |"
        )
    for title, mapping in (("Skipped", summary["skipped"]), ("Notes", summary["notes"])):
        if mapping:
            lines += ["", f"## {title}", ""] + [f"- {k}: {v}" for k, v in mapping.items()]
    lines += ["", "## Method", "", summary["method"], "", summary["attribution"], ""]
    return "\n".join(lines)


def write_outputs(result: BenchResult, matcher_name: str) -> Path:
    out = result.config.out
    out.mkdir(parents=True, exist_ok=True)
    summary = summary_dict(result, matcher_name)
    (out / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    (out / "summary.md").write_text(markdown(summary), encoding="utf-8")
    folder = out / "submissions"
    folder.mkdir(exist_ok=True)
    for arm in result.arms:
        payload = {
            "dataset_name": arm.dataset,
            "analyses": [a.submission_row() for a in arm.analyses],
        }
        (folder / f"{arm.dataset}__{arm.arm}.json").write_text(
            json.dumps(payload, indent=2) + "\n", encoding="utf-8"
        )
    return out / "summary.md"
