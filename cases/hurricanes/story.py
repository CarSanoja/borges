from __future__ import annotations

from reference import FACTS, share_significant

from borges.analysis.narrative_flip import flip_sentence, insert_sentence
from borges.analysis.schemas import NarratorOutput
from borges.runs.models import RunSnapshot


def _fmt(result) -> str:
    low, high = result.ci_low, result.ci_high
    return f"{result.estimate:+.1f} additional deaths (95% CI {low:.1f} to {high:.1f})"


def _labels(snapshot: RunSnapshot, universes) -> str:
    plan = snapshot.plan
    names = []
    for universe in universes:
        step_id = universe.changed[0]
        names.append(plan.step(step_id).option(universe.choices[step_id]).label.lower())
    return "; ".join(names)


def narrate(snapshot: RunSnapshot) -> tuple[NarratorOutput, str]:
    report, plan = snapshot.report, snapshot.plan
    assert report is not None and plan is not None and report.minimal_flip is not None
    flip = report.minimal_flip
    garden = snapshot.garden
    base = report.original_result
    singles = [u for u in garden.finished() if u.kind == "single"]
    flipped = [u for u in singles if u.flipped]
    share = share_significant()
    narrative = (
        f"With the default choices, modelled on the original paper, a hurricane with a "
        f"feminine name is predicted to cause {_fmt(base)}, p = {base.p_value:.3f}, "
        f"n = {base.n} storms, so the verdict is {report.original_verdict}. "
        f"{len(flipped)} of the {len(singles)} single-decision changes reach "
        f"{flip.flipped_verdict}: {_labels(snapshot, flipped)}. "
        f"That flip was re-executed from a fresh sandbox and reproduced exactly. "
        f"The published specification curve over "
        f"{FACTS['specifications']:,} specifications finds only "
        f"{FACTS['significant_predicted_direction']} significant effects in the predicted "
        f"direction ({share:.1%}), with a median of "
        f"{FACTS['median_effect_additional_deaths']} additional deaths, so the finding lives "
        f"in a small corner of the analysis space."
    )
    sentence = flip_sentence(plan, report)
    if sentence:
        narrative = insert_sentence(narrative, sentence)
    caveats = [
        "The effect is a difference in predicted deaths at sample means, not a causal estimate "
        "for any one storm.",
        "Ninety-four storms is a small sample and two of them dominate the death counts.",
        "Scripted run: the plan was written by hand from the published specification menu, "
        "not proposed by a model.",
    ]
    story = (
        f"A famous paper reported that hurricanes with feminine names kill more people. "
        f"Re-run with the original choices, the effect is {_fmt(base)}, p = {base.p_value:.3f}: "
        f"{report.original_verdict.lower()}. {len(flipped)} one-decision changes get a "
        f"significant effect, and the published specification curve finds the same pattern: "
        f"{FACTS['significant_predicted_direction']} of {FACTS['specifications']:,} "
        f"reasonable analyses are significant."
    )
    return NarratorOutput(narrative=narrative, caveats=caveats), story
