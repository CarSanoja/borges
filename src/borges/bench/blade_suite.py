from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from borges.bench.blade_adapter import AdaptedCase, build_case
from borges.bench.blade_convert import AgentAnalysis, convert_snapshot
from borges.bench.blade_cost import check_budget, estimate_usd
from borges.bench.blade_matcher import Matcher
from borges.bench.blade_metrics import evaluate
from borges.bench.blade_rules import RULES
from borges.bench.blade_runner import ARMS, run_arm, run_settings
from borges.bench.blade_source import (
    BladeDataset,
    BladeNotFound,
    annotated_ids,
    load_dataset,
    resolve_root,
)
from borges.bench.scripted_plans import install, scripted_ids
from borges.config import Settings


@dataclass
class BenchConfig:
    datasets: list[str]
    arms: list[str]
    llm: str
    out: Path
    max_usd: float = 2.0
    repeats: int = 1
    blade_dir: Path | None = None
    max_rows: int = 20000
    max_universes: int = 24
    settings: Settings = field(default_factory=Settings)
    repo_cases: Path | None = None


@dataclass
class ArmResult:
    dataset: str
    arm: str
    analyses: list[AgentAnalysis] = field(default_factory=list)
    run_ids: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    universes: int = 0
    run_cost_usd: float = 0.0
    metrics: dict[str, dict] = field(default_factory=dict)
    matcher_cost_usd: float = 0.0


@dataclass
class BenchResult:
    config: BenchConfig
    arms: list[ArmResult] = field(default_factory=list)
    skipped: dict[str, str] = field(default_factory=dict)
    notes: dict[str, str] = field(default_factory=dict)
    estimate_usd: float = 0.0
    aborted: str | None = None

    @property
    def total_cost(self) -> float:
        return sum(a.run_cost_usd + a.matcher_cost_usd for a in self.arms)


def select_datasets(config: BenchConfig, root: Path) -> tuple[list[str], dict[str, str]]:
    available = [d for d in annotated_ids(root) if d in RULES]
    wanted = available if config.datasets == ["all"] else config.datasets
    chosen: list[str] = []
    skipped: dict[str, str] = {}
    for dataset_id in wanted:
        if dataset_id not in available:
            skipped[dataset_id] = "no expert annotations or no decision rule"
        elif config.llm == "scripted" and dataset_id not in scripted_ids():
            skipped[dataset_id] = "no scripted plan; run with --llm nebius"
        else:
            chosen.append(dataset_id)
    return chosen, skipped


def validate_arms(arms: list[str]) -> list[str]:
    unknown = [a for a in arms if a not in ARMS]
    if unknown:
        raise ValueError(f"unknown arm {unknown}; choose from {', '.join(ARMS)}")
    return arms


def prepare(config: BenchConfig, dataset: BladeDataset, cases_dir: Path) -> AdaptedCase:
    adapted = build_case(dataset, cases_dir, config.max_rows, config.max_universes)
    if config.llm == "scripted":
        repo = config.repo_cases or config.settings.borges_cases_dir
        if not install(dataset.id, adapted.case_dir, repo):
            raise BladeNotFound(f"no scripted fixtures for {dataset.id}")
    return adapted


async def run_arms_for(
    config: BenchConfig, dataset: BladeDataset, adapted: AdaptedCase, arm: str, result: BenchResult
) -> ArmResult:
    outcome = ArmResult(dataset.id, arm)
    seen: set[str] = set()
    for repeat in range(config.repeats):
        if config.llm != "scripted" and result.total_cost + outcome.run_cost_usd > config.max_usd:
            result.aborted = f"stopped before {dataset.id}/{arm}: spend reached ${config.max_usd}"
            outcome.errors.append(result.aborted)
            break
        settings = run_settings(
            config.settings, config.out, adapted.case_dir.parent, repeat, f"{dataset.id}/{arm}"
        )
        snapshot = await run_arm(settings, adapted, arm, config.llm, repeat, config.max_universes)
        outcome.run_ids.append(snapshot.run_id)
        outcome.run_cost_usd += snapshot.usage.cost_usd
        if snapshot.status != "completed":
            outcome.errors.append(f"{snapshot.run_id}: {snapshot.error}")
            continue
        outcome.universes += len(snapshot.garden.finished())
        for analysis in convert_snapshot(snapshot, adapted.rule, dataset.columns):
            if analysis.signature not in seen:
                seen.add(analysis.signature)
                outcome.analyses.append(analysis)
    return outcome


async def score(
    matcher: Matcher, dataset: BladeDataset, adapted: AdaptedCase, outcome: ArmResult
) -> None:
    before = matcher.usage.cost_usd
    failed = matcher.usage.failed_chunks
    expert = {k: dataset.items(k) for k in ("cvar", "model", "transform")}
    outcome.metrics = await evaluate(
        matcher,
        adapted.rule.question,
        ", ".join(f"{c}: {d}" for c, d in dataset.columns.items())[:3000],
        expert,
        [a.items for a in outcome.analyses],
    )
    outcome.matcher_cost_usd = matcher.usage.cost_usd - before
    if matcher.usage.failed_chunks > failed:
        outcome.errors.append(
            f"matcher: {matcher.usage.failed_chunks - failed} chunk(s) returned invalid JSON "
            "twice and were scored as unmatched"
        )


async def run_benchmark(config: BenchConfig, matcher: Matcher, llm_matcher: bool) -> BenchResult:
    validate_arms(config.arms)
    root = resolve_root(config.blade_dir)
    chosen, skipped = select_datasets(config, root)
    result = BenchResult(config=config, skipped=skipped)
    if config.llm != "scripted":
        result.estimate_usd = estimate_usd(len(chosen), config.arms, config.repeats, llm_matcher)
        check_budget(result.estimate_usd, config.max_usd)
    cases_dir = config.out / "cases"
    for dataset_id in chosen:
        dataset = load_dataset(root, dataset_id)
        adapted = prepare(config, dataset, cases_dir)
        if adapted.note:
            result.notes[dataset_id] = adapted.note
        for arm in config.arms:
            outcome = await run_arms_for(config, dataset, adapted, arm, result)
            if outcome.analyses:
                await score(matcher, dataset, adapted, outcome)
            result.arms.append(outcome)
    return result
