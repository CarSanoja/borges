from __future__ import annotations

from borges.analysis.models import Judgement
from borges.analysis.narrative_original import original_sentence
from borges.analysis.narrative_robustness import robustness_sentence
from borges.analysis.narrator import narrate
from borges.analysis.narrator_garden import (
    NARRATOR_INPUT_BUDGET_TOKENS,
    estimate_tokens,
    garden_digest,
)
from borges.analysis.prompts.narrator import SYSTEM
from borges.analysis.schemas import NarratorOutput
from borges.garden.influence import build_report
from borges.runs.judged_ledger import JudgedLedger
from tests.analysis.fakes import FakeLLM
from tests.garden.synthetic import garden_of, option, plan_of, result, step_of, universe


def fixtures():
    plan = plan_of(
        step_of("rows", "filter", option("keep", True), option("drop")),
        step_of("model", "model", option("ols", True), option("logit")),
    )
    garden = garden_of(
        plan,
        universe(plan, {}, result(1.0)),
        universe(plan, {"rows": "drop"}, result(0.9)),
        universe(plan, {"model": "logit"}, result(-0.1, p=0.8)),
        universe(plan, {"rows": "drop", "model": "logit"}, result(-0.2, p=0.7)),
    )
    broken = universe(plan, {"model": "logit"}, result(0.0))
    broken.id, broken.status, broken.result, broken.error = "u_bad", "failed", None, "boom\ntrace"
    garden.add(broken)
    judged = JudgedLedger()
    judged.record(
        "model",
        plan.step("model").option("logit"),
        Judgement(defensibility=0.8, accepted=True, reason="standard alternative"),
    )
    return plan, garden, judged


def test_the_digest_lists_every_universe_with_decisions_and_results() -> None:
    plan, garden, judged = fixtures()
    digest, tokens = garden_digest(plan, garden, judged, ["a caveat"])
    rows = digest["universes"]
    assert len(rows) == 5
    by_id = {r["id"]: r for r in rows}
    assert by_id[garden.baseline_id]["changes"] == []
    assert by_id[garden.baseline_id]["ci"] == [0.8, 1.2]
    combo = next(r for r in rows if len(r["changes"]) == 2)
    assert combo["changes"] == ["Step rows: label drop", "Step model: label logit"]
    assert combo["flipped"] is True
    assert by_id["u_bad"]["failed"] == "boom"
    assert digest["judge_verdicts"][0]["reason"] == "standard alternative"
    assert digest["caveats"] == ["a caveat"]
    assert tokens > 0


def test_over_budget_digests_are_thinned_in_steps_and_never_lose_the_flips() -> None:
    plan, garden, judged = fixtures()
    full, full_tokens = garden_digest(plan, garden, judged, [])
    slim, slim_tokens = garden_digest(plan, garden, judged, [], budget=full_tokens - 1)
    assert slim["detail"] == "estimate and p only"
    assert "ci" not in slim["universes"][0] and len(slim["universes"]) == 5
    tiny, _ = garden_digest(plan, garden, judged, [], budget=1)
    assert tiny["detail"] == "baseline, flipped and failed only"
    assert {r["id"] for r in tiny["universes"]} == {
        garden.baseline_id,
        "u_bad",
        *(u.id for u in garden.universes.values() if u.flipped),
    }
    assert NARRATOR_INPUT_BUDGET_TOKENS >= 100_000
    assert slim_tokens < full_tokens


async def test_narrate_feeds_the_whole_garden_and_records_the_input_tokens() -> None:
    plan, garden, judged = fixtures()
    report = build_report(plan, garden, None)
    text = f"{original_sentence(report)} Plain. {robustness_sentence(report)}"
    llm = FakeLLM({"narrator": NarratorOutput(narrative=text, caveats=[])})
    await narrate(llm, plan, report, garden, judged)
    content = llm.calls[0].messages[1]["content"]
    assert "Garden:" in content and "u_bad" in content and "standard alternative" in content
    expected = sum(estimate_tokens(m["content"]) for m in llm.calls[0].messages)
    assert report.narrator_input_tokens == expected
    assert "narrator_input_tokens" not in content


async def test_narrate_without_a_garden_keeps_the_report_only_prompt() -> None:
    plan, garden, _ = fixtures()
    report = build_report(plan, garden, None)
    llm = FakeLLM({"narrator": NarratorOutput(narrative="Plain.", caveats=[])})
    await narrate(llm, plan, report)
    assert "Garden:" not in llm.calls[0].messages[1]["content"]


def test_the_narrator_prompt_asks_for_the_whole_garden() -> None:
    text = " ".join(SYSTEM.split())
    assert "the whole garden" in text and "every universe" in text
