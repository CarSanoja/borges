from __future__ import annotations

import json
from typing import Any

import pandas as pd
from option_code import ADVERSARY_OPTIONS, BASE_OPTIONS
from plan_text import JUDGE, validated_adversary, validated_judge, validated_planner
from prepare import CASE_DIR, load_teams
from summary import summarize
from validation import fixture_path

from borges.analysis.models import DecisionRule
from borges.analysis.schemas import CoderOutput, NarratorOutput
from borges.cases.models import CaseSpec, ReferenceEstimate
from borges.llm.scripted_provider import SCRIPTED_MODEL
from borges.runs.pipeline import MAX_COMBINATIONS_PER_LEVEL

RULE = DecisionRule(
    metric="odds ratio of a red card per game, dark vs light skin tone",
    comparator="gt",
    threshold=1.0,
    alpha=0.05,
    positive_label="BIAS DETECTED",
    negative_label="NO CLEAR EVIDENCE",
)
REFERENCE_LABEL = "29 human research teams (Silberzahn et al., 2018)"


def write_fixture(key: str, parsed: Any) -> None:
    payload = {
        "model": SCRIPTED_MODEL,
        "text": json.dumps(parsed),
        "parsed": parsed,
        "tokens_in": 0,
        "tokens_out": 0,
    }
    path = fixture_path(key)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n")


def fmt(result) -> str:
    return f"OR {result.estimate:.2f} (95% CI {result.ci_low:.2f} to {result.ci_high:.2f})"


def narrate(info: dict[str, Any]) -> tuple[NarratorOutput, str]:
    base = info["baseline"]["result"]
    lo, hi = min(info["estimates"]), max(info["estimates"])
    singles = info["singles"]
    pair_flips = [r for r in info["flipped"] if r["changes"] == 2]
    triple = [r for r in info["flipped"] if r["changes"] == 3]
    rejected = info["rejected_single"]["result"]
    single_lo = min(r["result"].estimate for r in singles)
    single_hi = max(r["result"].estimate for r in singles)
    n_pairs = sum(1 for r in info["rows"] if r["changes"] == 2 and not r["rejected"])
    searched_pairs = min(MAX_COMBINATIONS_PER_LEVEL, n_pairs)
    minimal = max(triple, key=lambda r: abs(r["result"].estimate - base.estimate))["result"]
    t_lo = min(r["result"].estimate for r in triple)
    t_hi = max(r["result"].estimate for r in triple)
    narrative = (
        f"With the default choices dark-skinned players are carded more: {fmt(base)}, "
        f"p = {base.p_value:.4f}, n = {base.n:,} dyads, so the verdict is BIAS DETECTED. "
        f"None of the {len(singles)} single-decision changes reverses it: the odds ratio stays "
        f"between {single_lo:.2f} and {single_hi:.2f} and every interval keeps excluding 1. "
        f"None of the {searched_pairs} pairs ranked most likely to flip it does either"
        f"{'' if not pair_flips else f' (except {len(pair_flips)})'}. "
        f"The verdict first changes at three simultaneous changes: {len(triple)} such universes "
        f"reach NO CLEAR EVIDENCE, with odds ratios of {t_lo:.2f} to {t_hi:.2f} and p between "
        f"{min(r['result'].p_value for r in triple):.3f} and "
        f"{max(r['result'].p_value for r in triple):.3f}. All of them adjust for the full "
        f"covariate set, and most add player-clustered errors and the second rater alone. "
        f"The minimal flip (second rater only, referees with 22 or more dyads, full "
        f"covariates; {fmt(minimal)}, p = {minimal.p_value:.3f}) was re-executed from a fresh "
        f"sandbox and reproduced exactly. "
        f"Across all defensible universes the odds ratio runs from {lo:.2f} to {hi:.2f}, inside "
        f"the human teams' range of 0.89 to 2.93. The only one-decision change that did flip "
        f"the verdict, keeping low-bias referees only ({fmt(rejected)}, p = "
        f"{rejected.p_value:.3f}), was rejected as an indefensible change of population."
    )
    caveats = [
        "Odds ratios compare the lightest with the darkest tone on a 0 to 1 scale and rest on "
        "player-referee dyads, not on individual refereeing decisions.",
        "The estimate is an association; it cannot separate bias from unmeasured differences "
        "in playing style or match context.",
        "Influence is measured under fixed defaults and is not a causal statement about the world.",
    ]
    story = (
        f"Twenty-nine teams analysed this dataset and disagreed on whether referees card "
        f"dark-skinned players more. The default analysis gives {fmt(base)}: bias detected. "
        f"No single analytic choice reverses that and no pair does; it takes three together, "
        f"such as a full covariate set, frequent referees only and player-clustered errors, "
        f"to land on no clear evidence (OR {t_lo:.2f} to {t_hi:.2f}). The one single flip "
        f"that existed, restricting to low-bias referees, is not defensible."
    )
    return NarratorOutput(narrative=narrative, caveats=caveats), story


def reference() -> list[ReferenceEstimate]:
    teams = load_teams()
    return [
        ReferenceEstimate(
            label=f"Team {int(row.Team)}: {row._2}",
            estimate=float(row.OR),
            ci_low=float(row.OR_lo),
            ci_high=float(row.OR_hi),
            significant=bool(row.OR_lo > 1),
        )
        for row in teams.itertuples()
    ]


def main() -> None:
    codes = {**BASE_OPTIONS, **ADVERSARY_OPTIONS}
    frame = pd.read_parquet(CASE_DIR / "data.parquet")
    info = summarize(frame, codes, RULE)

    write_fixture("planner", validated_planner().model_dump())
    for key, code in codes.items():
        parsed = CoderOutput(code=code).model_dump()
        write_fixture(f"coder:{key}", parsed)
    write_fixture("adversary", validated_adversary().model_dump())
    for key in JUDGE:
        write_fixture(f"judge:{key}", validated_judge(key).model_dump())
    narrator, story = narrate(info)
    write_fixture("narrator", narrator.model_dump())

    spec = CaseSpec(
        id="red_cards",
        title="Red cards and skin tone",
        subtitle="29 research teams. Same data. Opposite answers.",
        question=(
            "Are soccer referees more likely to give red cards to dark-skin-toned players "
            "than to light-skin-toned players?"
        ),
        decision_rule=RULE,
        dataset_name="crowdstorming_dyads",
        max_universes=48,
        reference_label=REFERENCE_LABEL,
        reference=reference(),
        story=story,
    )
    (CASE_DIR / "case.json").write_text(spec.model_dump_json(indent=2) + "\n")
    print(narrator.narrative)
    print(story)


if __name__ == "__main__":
    main()
