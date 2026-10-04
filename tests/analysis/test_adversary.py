from __future__ import annotations

from borges.analysis.adversary import propose_options
from borges.analysis.models import AnalysisResult, StepTrace
from borges.analysis.schemas import AdversaryOutput, ProposedOption
from borges.garden.models import Universe
from borges.llm.client import Role
from tests.analysis.fakes import FakeLLM, make_plan


def proposed(step_id: str, option_id: str, spec: str | None = None) -> ProposedOption:
    return ProposedOption(
        step_id=step_id,
        id=option_id,
        label=f"L {option_id}",
        rationale="r",
        spec=spec or f"spec {option_id}",
        source="src",
    )


def baseline() -> Universe:
    return Universe(
        id="u0",
        choices={"d1": "keep", "m1": "ols"},
        kind="baseline",
        status="done",
        result=AnalysisResult(estimate=0.4, ci_low=0.1, ci_high=0.7, p_value=0.01, n=100),
        verdict="SHIP",
        traces=[StepTrace(step_id="d1", option_id="keep", rows_before=100, rows_after=97)],
    )


async def test_maps_and_filters_proposals() -> None:
    out = AdversaryOutput(
        proposals=[
            proposed("d1", "winsor"),
            proposed("d1", "adv_winsor"),
            proposed("zz", "unknown"),
            proposed("d1", "clip"),
            proposed("m1", "other", spec="  SPEC for welch ON outcome "),
            proposed("m1", "robust"),
            proposed("d1", "late"),
        ]
    )
    llm = FakeLLM({"adversary": out})
    plan = make_plan()
    proposals = await propose_options(llm, plan, baseline(), max_proposals=3)
    assert [(p.step_id, p.option.id) for p in proposals] == [
        ("d1", "adv_winsor"),
        ("d1", "adv_clip"),
        ("m1", "adv_robust"),
    ]
    option = proposals[0].option
    assert option.origin == "adversary" and option.is_default is False
    assert option.source == "src"
    call = llm.calls[0]
    assert call.role is Role.ADVERSARY and call.key == "adversary" and call.max_tokens == 2500
    content = call.messages[1]["content"]
    assert "rows_after" in content and "SHIP" in content and "Returns at most" not in content


async def test_drops_duplicate_of_existing_id_and_spec() -> None:
    plan = make_plan()
    out = AdversaryOutput(
        proposals=[
            proposed("d1", "adv_x"),
            proposed("d1", "x"),
            proposed("d1", "adv_y", spec="Spec for trim on outcome"),
        ]
    )
    proposals = await propose_options(FakeLLM({"adversary": out}), plan, baseline())
    assert [p.option.id for p in proposals] == ["adv_x"]


async def test_drops_duplicate_of_existing_label_and_prefixed_id() -> None:
    plan = make_plan()
    same_label = proposed("d1", "fresh_id")
    same_label.label = "label  TRIM!"
    prefixed = proposed("d1", "adv_trim")
    prefixed.label = "Label trim as well"
    out = AdversaryOutput(proposals=[prefixed, same_label, proposed("d1", "genuinely_new")])
    proposals = await propose_options(FakeLLM({"adversary": out}), plan, baseline())
    assert [p.option.id for p in proposals] == ["adv_genuinely_new"]


async def test_coincidental_id_with_different_content_is_kept() -> None:
    plan = make_plan()
    out = AdversaryOutput(proposals=[proposed("d1", "adv_trim")])
    proposals = await propose_options(FakeLLM({"adversary": out}), plan, baseline())
    assert [p.option.id for p in proposals] == ["adv_trim"]


async def test_avoid_hints_reach_the_prompt_only_when_given() -> None:
    plan = make_plan()
    llm = FakeLLM({"adversary": AdversaryOutput(proposals=[])})
    await propose_options(llm, plan, baseline())
    await propose_options(
        llm, plan, baseline(), avoid=["Keep engaged only: keep engaged (rejected)"]
    )
    plain, steered = (call.messages[1]["content"] for call in llm.calls)
    assert "Earlier runs" not in plain
    assert "Earlier runs on this dataset" in steered
    assert "- Keep engaged only: keep engaged (rejected)" in steered


async def test_proposals_that_only_repeat_the_plan_are_asked_for_again() -> None:
    repeats = AdversaryOutput(proposals=[proposed("m1", "other", spec="Spec for welch on outcome")])
    fresh = AdversaryOutput(proposals=[proposed("d1", "clip")])
    llm = FakeLLM({"adversary": repeats, "adversary:retry": fresh})
    proposals = await propose_options(llm, make_plan(), baseline())
    assert [(p.step_id, p.option.id) for p in proposals] == [("d1", "adv_clip")]
    assert [c.key for c in llm.calls] == ["adversary", "adversary:retry"]
    assert "'L other'" in llm.calls[1].messages[-1]["content"]
