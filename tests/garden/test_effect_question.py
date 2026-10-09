from __future__ import annotations

import pytest

from borges.analysis.models import AnalysisPlan, DatasetProfile, DecisionRule, StepTrace
from borges.garden.effect_question import effect_question
from borges.garden.estimand import estimand_detail
from borges.garden.models import Universe


def plan(question: str, metric: str = "m") -> AnalysisPlan:
    return AnalysisPlan(
        question=question,
        estimand="e",
        decision_rule=DecisionRule(metric=metric),
        dataset=DatasetProfile(name="t", n_rows=1, columns=[]),
        steps=[],
    )


@pytest.mark.parametrize(
    "question",
    [
        "Did the data-analytics tool reduce budget overruns on our audit engagements?",
        "¿Aprobamos menos préstamos a mujeres que a hombres con el mismo perfil de riesgo?",
        "Do hurricanes with more feminine names cause more deaths?",
        "¿Funcionan las tutorías de matemáticas?",
    ],
)
def test_questions_about_an_effect_or_equal_profiles(question: str) -> None:
    assert effect_question(plan(question))


@pytest.mark.parametrize(
    "question",
    [
        "Are soccer referees more likely to give red cards to dark-skin-toned players?",
        "Do religious people self-report greater well-being?",
        "Is the reduction in overruns associated with team size?",
    ],
)
def test_questions_about_an_association(question: str) -> None:
    assert not effect_question(plan(question))


def universe(terms: list[str]) -> Universe:
    design: dict[str, object] = {"terms": terms, "exposure": "tool"}
    trace = StepTrace(step_id="model", option_id="o", rows_before=1, rows_after=1, design=design)
    return Universe(id="u", choices={}, kind="single", traces=[trace])


def test_adjusting_for_a_confounder_answers_the_same_effect_question() -> None:
    before, after = universe(["const", "tool"]), universe(["const", "tool", "revenue"])
    assert estimand_detail(before, after) is not None
    assert estimand_detail(before, after, effect=True) is None
