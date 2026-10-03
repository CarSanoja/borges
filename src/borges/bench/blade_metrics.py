from __future__ import annotations

from dataclasses import asdict, dataclass

from borges.bench.blade_matcher import MATCH_THRESHOLD, Matcher, MatchPair
from borges.bench.blade_source import Kind

KINDS: tuple[Kind, ...] = ("cvar", "model", "transform")


@dataclass(frozen=True)
class KindMetrics:
    kind: str
    n_expert: int
    n_agent_items: int
    matched_expert: int
    coverage: float
    hit_rate: float
    f1: float


def harmonic(a: float, b: float) -> float:
    return 0.0 if a + b == 0 else 2 * a * b / (a + b)


def kind_metrics(
    kind: Kind,
    expert: list[str],
    runs: list[list[str]],
    pairs_for: dict[str, list[MatchPair]],
    unique: list[str],
) -> KindMetrics:
    good = [p for p in pairs_for.get(kind, []) if p.similarity >= MATCH_THRESHOLD]
    matched_expert = {p.expert for p in good}
    matched_agent = {p.agent for p in good}
    index = {text: i for i, text in enumerate(unique)}
    rates = []
    for items in runs:
        if items:
            hits = sum(1 for text in items if index[text] in matched_agent)
            rates.append(hits / len(items))
    denominator = len(expert)
    if kind == "model":
        denominator = min(len(expert), len(runs))
    coverage = min(1.0, len(matched_expert) / denominator) if denominator else 0.0
    hit_rate = sum(rates) / len(rates) if rates else 0.0
    return KindMetrics(
        kind=kind,
        n_expert=len(expert),
        n_agent_items=len(unique),
        matched_expert=len(matched_expert),
        coverage=coverage,
        hit_rate=hit_rate,
        f1=harmonic(coverage, hit_rate),
    )


async def evaluate(
    matcher: Matcher,
    question: str,
    schema: str,
    expert: dict[Kind, list[str]],
    runs: list[dict[Kind, list[str]]],
) -> dict[str, dict]:
    results: dict[str, dict] = {}
    for kind in KINDS:
        per_run = [run.get(kind, []) for run in runs]
        unique = list(dict.fromkeys(text for items in per_run for text in items))
        pairs: list[MatchPair] = []
        if unique and expert.get(kind):
            pairs = await matcher.match(kind, question, schema, expert[kind], unique)
        metrics = kind_metrics(kind, expert.get(kind, []), per_run, {kind: pairs}, unique)
        results[kind] = {
            **asdict(metrics),
            "pairs": [asdict(p) for p in pairs if p.similarity >= MATCH_THRESHOLD],
        }
    return results


def mean_f1(metrics: dict[str, dict]) -> float:
    return sum(metrics[k]["f1"] for k in KINDS) / len(KINDS)
