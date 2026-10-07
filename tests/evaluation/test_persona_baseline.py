from __future__ import annotations

from borges.analysis.models import DecisionRule
from borges.analysis.schemas import PlannerOutput
from borges.evaluation.persona_baseline import PERSONAS, persona_plan, with_persona
from borges.llm.client import Role
from tests.analysis.fakes import FakeLLM, make_profile
from tests.analysis.test_planner import popt, pstep

OUTPUT = PlannerOutput(
    estimand="E",
    steps=[
        pstep("f1", "filter", [popt("a"), popt("b", True)]),
        pstep("m", "model", [popt("ols", True), popt("welch")]),
    ],
)


def test_the_persona_leads_the_system_message_and_the_rest_is_unchanged() -> None:
    messages = [{"role": "system", "content": "S"}, {"role": "user", "content": "U"}]
    changed = with_persona(messages, "an economist")
    assert changed[0]["content"].startswith("You are an economist. Plan the analysis you")
    assert changed[0]["content"].endswith("S") and changed[1] == messages[1]
    assert messages[0]["content"] == "S"


async def test_each_analyst_runs_only_its_own_defaults_under_its_own_key() -> None:
    llm = FakeLLM({"planner:persona3": OUTPUT})
    plan = await persona_plan(llm, make_profile(), "Q?", DecisionRule(metric="m"), 3)
    assert [[o.id for o in s.options] for s in plan.steps] == [["b"], ["ols"]]
    call = llm.calls[0]
    assert call.role is Role.PLANNER and call.key == "planner:persona3"
    assert call.messages[0]["content"].startswith(f"You are {PERSONAS[3]}.")
