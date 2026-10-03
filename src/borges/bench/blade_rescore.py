from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from borges.bench.blade_adapter import AdaptedCase
from borges.bench.blade_convert import convert_snapshot
from borges.bench.blade_matcher import MAX_TOKENS, LLMMatcher, Matcher, MissingReply
from borges.bench.blade_rules import RULES
from borges.bench.blade_source import BladeNotFound, load_dataset, resolve_root
from borges.bench.blade_suite import ArmResult, BenchConfig, BenchResult, score
from borges.llm.cache import cache_key
from borges.runs.store import RunStore

RESCORE_DIR = "rescore"


@dataclass
class CachedMatcher(LLMMatcher):
    async def _ask(self, messages: list[dict[str, str]]) -> tuple[str, str | None]:
        key = cache_key(self.model.id, messages, "match-json", MAX_TOKENS, 0.0)
        cached = self.cache.get(key) if self.cache else None
        self.usage.calls += 1
        if cached is None:
            raise MissingReply(f"no cached reply for {key[:12]}")
        self.usage.cached_calls += 1
        return str(cached["text"]), None


def read_rows(out: Path) -> list[dict]:
    path = out / "summary.json"
    if not path.is_file():
        raise BladeNotFound(f"{path} not found; point --out at a finished benchmark folder")
    return json.loads(path.read_text(encoding="utf-8"))["rows"]


def rebuild_arm(out: Path, row: dict, columns: dict[str, str]) -> tuple[ArmResult, str | None]:
    dataset_id, arm = row["dataset"], row["arm"]
    outcome = ArmResult(dataset_id, arm, run_ids=list(row["run_ids"]))
    store = RunStore(out / "runs" / dataset_id / arm)
    seen: set[str] = set()
    problems: list[str] = []
    for run_id in row["run_ids"]:
        if not store.exists(run_id):
            problems.append(f"{run_id}: run folder missing")
            continue
        snapshot = store.snapshot(run_id)
        outcome.run_cost_usd += snapshot.usage.cost_usd
        if snapshot.status != "completed":
            problems.append(f"{run_id}: {snapshot.status} {snapshot.error or ''}".strip())
            continue
        outcome.universes += len(snapshot.garden.finished())
        for analysis in convert_snapshot(snapshot, RULES[dataset_id], columns):
            if analysis.signature not in seen:
                seen.add(analysis.signature)
                outcome.analyses.append(analysis)
    return outcome, "; ".join(problems) or None


def adapted_for(dataset_id: str) -> AdaptedCase:
    rule = RULES[dataset_id]
    return AdaptedCase(f"blade_{dataset_id}", Path("."), rule, 0, 0, None)


async def rescore(
    out: Path, matcher: Matcher, blade_dir: Path | None, datasets: list[str] | None = None
) -> BenchResult:
    root = resolve_root(blade_dir)
    config = BenchConfig(datasets or ["all"], ["planner", "adversary"], "nebius", out / RESCORE_DIR)
    result = BenchResult(config=config)
    for row in read_rows(out):
        dataset_id = row["dataset"]
        if datasets and dataset_id not in datasets:
            continue
        dataset = load_dataset(root, dataset_id)
        outcome, problem = rebuild_arm(out, row, dataset.columns)
        label = f"{dataset_id}/{row['arm']}"
        if not outcome.analyses:
            result.skipped[label] = problem or "the run produced no analyses"
            continue
        if problem:
            result.notes[label] = f"some runs did not complete: {problem}"
        await score(matcher, dataset, adapted_for(dataset_id), outcome)
        result.arms.append(outcome)
    return result
