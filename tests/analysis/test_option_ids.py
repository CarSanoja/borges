from __future__ import annotations

from borges.analysis.adversary import propose_options
from borges.analysis.ids import slug_id
from borges.analysis.models import DecisionRule
from borges.analysis.planner import plan_analysis
from borges.analysis.schemas import (
    AdversaryOutput,
    PlannedOption,
    PlannedStep,
    PlannerOutput,
    ProposedOption,
    ReviewerOutput,
    ReviewVerdict,
)
from tests.analysis.fakes import FakeLLM, make_plan, make_profile
from tests.analysis.test_adversary import baseline


def test_slug_id_strips_lowercases_and_slugs() -> None:
    assert slug_id(" ols_basic") == "ols_basic"
    assert slug_id("\tOLS Basic\n") == "ols_basic"
    assert slug_id("  Winsor-1%  ") == "winsor_1"
    assert slug_id("   ") == ""


def test_schemas_normalise_ids_at_parse_time() -> None:
    option = PlannedOption(id=" OLS_Basic", label="l", rationale="r", spec="s")
    assert option.id == "ols_basic"
    step = PlannedStep(id=" Model ", title="t", kind="model", description="d", options=[option])
    assert step.id == "model"
    proposal = ProposedOption(
        step_id=" d1", id=" Clip ", label="l", rationale="r", spec="s", source=None
    )
    assert (proposal.step_id, proposal.id) == ("d1", "clip")
    verdict = ReviewVerdict(option_id=" adv_clip", faithful=True)
    assert verdict.option_id == "adv_clip"
    parsed = ReviewerOutput.model_validate({"verdicts": [{"option_id": " x ", "faithful": True}]})
    assert parsed.verdicts[0].option_id == "x"


async def test_planner_ids_with_leading_space_are_normalised() -> None:
    def opts(*ids: str) -> list[PlannedOption]:
        return [
            PlannedOption(id=i, label=f"l{i}", rationale="r", spec=f"s{i}", is_default=n == 0)
            for n, i in enumerate(ids)
        ]

    out = PlannerOutput(
        estimand="e",
        steps=[
            PlannedStep(
                id=" d1", title="t", kind="filter", description="", options=opts(" keep", "drop")
            ),
            PlannedStep(
                id="d2",
                title="t",
                kind="transform",
                description="",
                options=opts("a", "b"),
                produces=["x"],
            ),
            PlannedStep(
                id="d3",
                title="t",
                kind="feature",
                description="",
                options=opts("a", "b"),
                produces=["y"],
            ),
            PlannedStep(
                id="m",
                title="t",
                kind="model",
                description="",
                options=opts(" ols_basic", "ols_hc3"),
            ),
        ],
    )
    llm = FakeLLM({"planner": out})
    plan = await plan_analysis(llm, make_profile(), "q", DecisionRule(metric="diff", threshold=0.0))
    ids = {s.id: [o.id for o in s.options] for s in plan.steps}
    assert ids["d1"] == ["keep", "drop"]
    assert ids["m"] == ["ols_basic", "ols_hc3"]
    assert plan.step("m").default.id == "ols_basic"


async def test_adversary_ids_with_leading_space_get_prefix_and_dedupe() -> None:
    out = AdversaryOutput(
        proposals=[
            ProposedOption(step_id=" d1", id=" winsor", label="a", rationale="r", spec="spec one"),
            ProposedOption(
                step_id="d1", id="ADV_winsor", label="b", rationale="r", spec="spec two"
            ),
            ProposedOption(step_id="d1", id=" ", label="c", rationale="r", spec="spec three"),
        ]
    )
    proposals = await propose_options(
        FakeLLM({"adversary": out}), make_plan(), baseline(), max_proposals=4
    )
    assert [(p.step_id, p.option.id) for p in proposals] == [
        ("d1", "adv_winsor"),
        ("d1", "adv_option"),
    ]
