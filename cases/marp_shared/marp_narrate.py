from __future__ import annotations

from borges.analysis.models import AnalysisResult
from borges.analysis.narrative_flip import flip_sentence, insert_sentence
from borges.analysis.schemas import NarratorOutput
from borges.runs.models import RunSnapshot

RQ_CLAIM = {
    1: "religiosity goes with higher well-being",
    2: "the religiosity-well-being relation grows with perceived cultural norms",
}
RQ_TERM = {1: "beta", 2: "interaction beta"}


def fmt_p(p: float) -> str:
    return "p < 0.001" if p < 0.001 else f"p = {p:.3f}"


def fmt_result(rq: int, result: AnalysisResult) -> str:
    return (
        f"{RQ_TERM[rq]} = {result.estimate:.3f} (95% CI {result.ci_low:.3f} to "
        f"{result.ci_high:.3f}), {fmt_p(result.p_value)}, n = {result.n:,}"
    )


def team_sentence(teams: dict[str, float]) -> str:
    n, k = int(teams["n_teams"]), int(teams["n_significant"])
    return (
        f"The {n} research teams that reported a standardised effect range from "
        f"{teams['min']:.3f} to {teams['max']:.3f} (median {teams['median']:.3f}), and "
        f"{k} of them ({k / n:.0%}) have an interval above zero."
    )


def run_numbers(snapshot: RunSnapshot) -> dict[str, float]:
    done = [u for u in snapshot.garden.universes.values() if u.status == "done" and u.result]
    results = [u.result for u in done]
    return {
        "n_done": len(done),
        "n_single": sum(1 for u in done if u.kind == "single"),
        "n_combination": sum(1 for u in done if u.kind == "combination"),
        "estimate_min": min(r.estimate for r in results),
        "estimate_max": max(r.estimate for r in results),
        "ci_low_min": min(r.ci_low for r in results),
        "p_max": max(r.p_value for r in results),
    }


def _flip_clause(snapshot: RunSnapshot, rq: int) -> str:
    flip = snapshot.flip
    steps = "; ".join(f"{c.step_title.lower()}: {c.to_label}" for c in flip.changes)
    kind = "a single change" if len(flip.changes) == 1 else f"{len(flip.changes)} changes"
    repro = (
        " Re-running it in a fresh sandbox reproduced the same numbers." if flip.reproduced else ""
    )
    sign = "stays positive" if flip.flipped_result.estimate > 0 else "turns negative"
    return (
        f"The nearest verdict change takes {kind} ({steps}): "
        f"{fmt_result(rq, flip.flipped_result)}. The estimate {sign}; it is the p-value that "
        f"crosses 0.05.{repro}"
    )


def narrate(snapshot: RunSnapshot, rq: int, teams: dict[str, float]) -> NarratorOutput:
    report = snapshot.report
    nums = run_numbers(snapshot)
    base = report.original_result
    opening = (
        f"With the default choices, {RQ_CLAIM[rq]}: {fmt_result(rq, base)}, so the verdict is "
        f"{report.original_verdict}. Borges ran {nums['n_done']} universes: the baseline, "
        f"{nums['n_single']} single changes and {nums['n_combination']} combinations."
    )
    if report.minimal_flip is None:
        middle = (
            f"No flip was found: all {report.n_universes} universes keep the verdict "
            f"(design-weighted robustness {report.robustness:.0%}); the estimate runs from "
            f"{nums['estimate_min']:.3f} to {nums['estimate_max']:.3f}, the lowest interval "
            f"bound is {nums['ci_low_min']:.3f} and the largest p-value is "
            f"{fmt_p(nums['p_max'])}."
        )
    else:
        middle = (
            f"{report.n_flipped} of {report.n_universes} universes change the verdict "
            f"(design-weighted robustness {report.robustness:.0%}); the estimate runs from "
            f"{nums['estimate_min']:.3f} to {nums['estimate_max']:.3f}. "
            + _flip_clause(snapshot, rq)
        )
    narrative = " ".join([opening, middle, team_sentence(teams)])
    sentence = flip_sentence(snapshot.plan, report) if snapshot.plan is not None else None
    if sentence is not None:
        narrative = insert_sentence(narrative, sentence)
    caveats = [
        "The robustness figure comes from a uniform random sample of the option grid, which is "
        "built from the choices the teams documented; the share among all explored universes "
        "leans toward flips because the search chases them. Neither is a population estimate.",
        "Standardised coefficients describe an association in a convenience sample of 24 "
        "countries; they do not show that religion causes well-being.",
    ]
    if report.n_failed:
        caveats.append(f"{report.n_failed} universes failed to run and are excluded.")
    return NarratorOutput(narrative=narrative, caveats=caveats)


def story(snapshot: RunSnapshot, rq: int, teams: dict[str, float]) -> str:
    report = snapshot.report
    n, k = int(teams["n_teams"]), int(teams["n_significant"])
    lead = (
        f"{n} research teams analysed this dataset; {k} found that {RQ_CLAIM[rq]} with an "
        f"interval above zero. The default analysis gives {fmt_result(rq, report.original_result)}."
    )
    if report.minimal_flip is None:
        return f"{lead} Borges found no defensible flip in {report.n_universes} universes."
    steps = "; ".join(c.to_label for c in report.minimal_flip.changes)
    return (
        f"{lead} The verdict changes in {report.n_flipped} of {report.n_universes} universes; "
        f"the nearest is {steps}: {fmt_result(rq, report.minimal_flip.flipped_result)}."
    )
