from __future__ import annotations

import math
from dataclasses import dataclass

from borges.analysis.models import AnalysisPlan
from borges.garden.models import Garden, NoopOption, RobustnessBasis, Universe
from borges.garden.noop import has_noop, noop_pairs, single_universe
from borges.garden.result_key import result_key
from borges.garden.sampling import MIN_SAMPLE

MIN_DISTINCT_TO_RATE = 10
Z95 = 1.959963984540054


@dataclass(frozen=True)
class RobustnessFigures:
    headline: float
    basis: RobustnessBasis
    beam: float | None
    design: float | None
    design_note: str | None
    low: float | None
    high: float | None
    n_distinct: int
    rating: float | None
    rating_reason: str | None


def counted_universes(garden: Garden, noops: list[NoopOption]) -> list[Universe]:
    pairs = noop_pairs(noops)
    return [
        u
        for u in garden.finished()
        if u.kind != "verification" and (u.kind == "baseline" or not has_noop(u, pairs))
    ]


def distinct_universes(pool: list[Universe]) -> list[Universe]:
    chosen: dict[tuple[float, float, float, int], Universe] = {}
    for universe in sorted(pool, key=lambda u: (u.kind != "baseline", len(u.changed), u.id)):
        if universe.result is None:
            continue
        chosen.setdefault(result_key(universe.result), universe)
    return list(chosen.values())


def beam_share(garden: Garden, noops: list[NoopOption]) -> tuple[float | None, int]:
    baseline = garden.baseline
    distinct = distinct_universes(counted_universes(garden, noops))
    if baseline is None or not distinct:
        return None, 0
    agreeing = sum(1 for u in distinct if u.verdict == baseline.verdict)
    return agreeing / len(distinct), len(distinct)


def wilson(agreeing: int, total: int) -> tuple[float, float]:
    share = agreeing / total
    spread = Z95 * math.sqrt(share * (1 - share) / total + Z95**2 / (4 * total**2))
    centre = share + Z95**2 / (2 * total)
    scale = 1 + Z95**2 / total
    return max(0.0, (centre - spread) / scale), min(1.0, (centre + spread) / scale)


def sampled_share(garden: Garden, noops: list[NoopOption]) -> tuple[int, int, int] | None:
    baseline = garden.baseline
    if baseline is None or baseline.result is None or not garden.sample_ids:
        return None
    pairs = noop_pairs(noops)
    drawn = [garden.universes.get(uid) for uid in garden.sample_ids]
    pool = [u for u in drawn if u is not None and u.status == "done" and u.result is not None]
    distinct = distinct_universes([u for u in pool if not has_noop(u, pairs)])
    if len(distinct) < MIN_SAMPLE:
        return None
    agreeing = sum(1 for u in distinct if u.verdict == baseline.verdict)
    return agreeing, len(distinct), len(garden.sample_ids)


def single_decision_share(
    plan: AnalysisPlan, garden: Garden, noops: list[NoopOption]
) -> float | None:
    baseline = garden.baseline
    if baseline is None or baseline.result is None:
        return None
    pairs = noop_pairs(noops)
    base_key = result_key(baseline.result)
    shares: list[float] = []
    for step in plan.decision_steps:
        outcomes: dict[tuple[float, float, float, int], bool] = {}
        for option in step.options:
            if option.id == step.default.id or (step.id, option.id) in pairs:
                continue
            single = single_universe(garden, step.id, option.id)
            if single is None or single.result is None:
                continue
            key = result_key(single.result)
            if key != base_key:
                outcomes[key] = single.verdict == baseline.verdict
        if not outcomes:
            continue
        shares.append((1 + sum(outcomes.values())) / (1 + len(outcomes)))
    return sum(shares) / len(shares) if shares else None


@dataclass(frozen=True)
class DesignShare:
    share: float | None
    note: str | None
    low: float | None = None
    high: float | None = None


def design_share(plan: AnalysisPlan, garden: Garden, noops: list[NoopOption]) -> DesignShare:
    sample = sampled_share(garden, noops)
    if sample is not None and garden.sample_kind == "grid":
        agreeing, distinct, cells = sample
        return DesignShare(
            agreeing / distinct,
            f"the whole grid: {cells} combinations, {distinct} distinct results; exact, not "
            "sampled, and independent of the beam search",
        )
    if sample is not None:
        agreeing, distinct, draws = sample
        low, high = wilson(agreeing, distinct)
        seed = f" (seed {garden.sample_seed})" if garden.sample_seed is not None else ""
        return DesignShare(
            agreeing / distinct,
            f"uniform random sample of the grid: {draws} draws{seed}, each decision picking each "
            f"of its options equally, {distinct} distinct results, 95% interval "
            f"{low:.0%} to {high:.0%}; independent of the beam search",
            low,
            high,
        )
    single = single_decision_share(plan, garden, noops)
    if single is None:
        return DesignShare(None, None)
    return DesignShare(
        single,
        "one decision changed at a time: each decision counts equally and each of its options "
        "equally; interactions between decisions are not covered",
    )


def robustness_figures(
    plan: AnalysisPlan, garden: Garden, noops: list[NoopOption]
) -> RobustnessFigures:
    beam, n_distinct = beam_share(garden, noops)
    found = design_share(plan, garden, noops)
    design, design_note = found.share, found.note
    if design is not None:
        headline, basis = design, "design_weighted"
    elif beam is not None:
        headline, basis = beam, "distinct_results"
    else:
        headline, basis = 1.0, "none"
    if n_distinct >= MIN_DISTINCT_TO_RATE:
        rating, reason = headline, None
    else:
        rating, reason = None, f"n={n_distinct}, too few to rate"
    low, high = (found.low, found.high) if basis == "design_weighted" else (None, None)
    return RobustnessFigures(
        headline, basis, beam, design, design_note, low, high, n_distinct, rating, reason
    )
