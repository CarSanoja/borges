from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
from option_code import CODES
from plan_content import adversary_proposals, planner_output
from planner_judgements import VERDICTS

from borges.analysis.models import AnalysisResult, DecisionRule
from borges.analysis.narrative_flip import insert_sentence
from borges.analysis.schemas import (
    AdversaryOutput,
    CoderOutput,
    JudgeOutput,
    NarratorOutput,
)
from borges.cases.judge_fixtures import planner_judge_outputs
from borges.cases.models import CaseSpec
from borges.llm.scripted_provider import SCRIPTED_MODEL

FLIP_SENTENCE = (
    'The minimal flip changes Internal traffic from "Keep all sessions" to '
    '"Exclude internal accounts".'
)

HERE = Path(__file__).parent
FIXTURES = HERE / "fixtures"
STEP_ORDER = ["internal_traffic", "bot_filter", "novelty_window", "unit", "model"]
DEFAULTS = {
    "internal_traffic": "keep_all",
    "bot_filter": "none",
    "novelty_window": "all_days",
    "unit": "sessions",
    "model": "two_prop_z",
}

RULE = DecisionRule(
    metric="conversion lift, treatment minus control (percentage points)",
    comparator="gt",
    threshold=0.0,
    alpha=0.05,
    positive_label="SHIP",
    negative_label="DON'T SHIP",
)

CASE = CaseSpec(
    id="checkout_ab",
    title="New checkout A/B test",
    subtitle="Your AI analyst says ship. Is that the only defensible answer?",
    question="Does the new checkout increase the conversion rate?",
    decision_rule=RULE,
    dataset_name="checkout_sessions",
    max_universes=40,
    story=(
        "Fourteen days of checkout sessions, randomised by user. The default analysis shows a "
        "significant lift and says ship. But employees and QA testers placed test orders "
        "through the new checkout, and one defensible filter removes them and erases the lift."
    ),
)


def run_universe(frame: pd.DataFrame, choices: dict[str, str]) -> AnalysisResult:
    ctx: dict = {}
    data = frame.copy()
    for step_id in STEP_ORDER:
        namespace: dict = {}
        exec(CODES[f"{step_id}.{choices[step_id]}"], namespace)
        if step_id == "model":
            return AnalysisResult(**namespace["estimate"](data, ctx))
        data = namespace["apply"](data, ctx)
    raise RuntimeError("plan has no model step")


def write_fixture(key: str, parsed: object) -> None:
    payload = parsed.model_dump(mode="json", exclude_none=False)
    text = json.dumps(payload, ensure_ascii=False)
    record = {
        "model": SCRIPTED_MODEL,
        "text": text,
        "parsed": payload,
        "tokens_in": 0,
        "tokens_out": 0,
    }
    path = FIXTURES / (key.replace(":", "__") + ".json")
    path.write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n")


def fmt(result: AnalysisResult) -> str:
    return (
        f"{result.estimate:+.2f} pp (95% CI {result.ci_low:+.2f} to {result.ci_high:+.2f}, "
        f"p = {result.p_value:.3f})"
    )


def narrator_output(frame: pd.DataFrame) -> NarratorOutput:
    base = run_universe(frame, DEFAULTS)
    flip = run_universe(frame, {**DEFAULTS, "internal_traffic": "exclude_internal"})
    internal = frame[frame["is_internal"]]
    share_t = (internal["variant"] == "treatment").mean() * 100
    internal_rate = internal["converted"].mean() * 100
    moves = {}
    for step_id in STEP_ORDER:
        for key in CODES:
            step, option = key.split(".")
            if step == step_id and option != DEFAULTS[step_id] and option != "adv_engaged_only":
                alt = run_universe(frame, {**DEFAULTS, step_id: option})
                moves[key] = abs(alt.estimate - base.estimate)
    runner_up = max(v for k, v in moves.items() if not k.startswith("internal"))
    narrative = (
        f"The default analysis reports a conversion lift of {fmt(base)} across "
        f"{base.n:,} sessions, which clears the rule and says {RULE.label(base)}. "
        f"That lift does not survive one defensible decision. {len(internal):,} sessions "
        f"come from internal accounts (employees and QA), {share_t:.0f}% of them landed in "
        f"the treatment arm, and {internal_rate:.0f}% of them converted because they were "
        f"test orders. Excluding internal accounts leaves {flip.n:,} sessions and a lift of "
        f"{fmt(flip)}, which says {RULE.label(flip)}. This is the single decision that moves "
        f"the estimate most ({moves['internal_traffic.exclude_internal']:.2f} pp); the next "
        f"largest, {runner_up:.2f} pp, "
        "leaves the verdict unchanged."
    )
    narrative = insert_sentence(narrative, FLIP_SENTENCE)
    caveats = [
        "Influence is measured by switching one decision at a time from the defaults; it is a "
        "statement about this analysis, not a causal claim about the world.",
        f"The no-effect reading rests on the {len(internal):,} flagged sessions being "
        "test traffic; confirm the is_internal flag with the data owner.",
        "Excluding internal accounts does not prove the new checkout has no effect, only that "
        "the data cannot distinguish it from zero.",
    ]
    return NarratorOutput(narrative=narrative, caveats=caveats)


def main() -> None:
    FIXTURES.mkdir(exist_ok=True)
    frame = pd.read_parquet(HERE / "data.parquet")
    (HERE / "case.json").write_text(CASE.model_dump_json(indent=2) + "\n")

    planner = planner_output()
    write_fixture("planner", planner)
    for key, output in planner_judge_outputs(planner, VERDICTS).items():
        write_fixture(f"judge:planner:{key}", output)
    for key, code in CODES.items():
        write_fixture(f"coder:{key}", CoderOutput(code=code))

    proposals = adversary_proposals()
    write_fixture("adversary", AdversaryOutput(proposals=proposals))
    verdicts = {
        "adv_ols_cluster_user": JudgeOutput(
            defensibility=0.74,
            accepted=True,
            reason=(
                "Clustering by the randomisation unit is a recognised correction when users "
                "contribute several sessions; it changes uncertainty, not the population."
            ),
            source=proposals[0].source,
        ),
        "adv_engaged_only": JudgeOutput(
            defensibility=0.35,
            accepted=False,
            reason=(
                "Engagement is measured after exposure to the variant, so conditioning on it "
                "changes the population and can bias the comparison; not a bot filter."
            ),
            source=None,
        ),
    }
    for proposal in proposals:
        key = f"{proposal.step_id}.{proposal.id}"
        write_fixture(f"judge:{key}", verdicts[proposal.id])
    write_fixture("narrator", narrator_output(frame))


if __name__ == "__main__":
    main()
