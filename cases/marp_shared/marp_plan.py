from __future__ import annotations

from marp_counts import team_choice_counts
from marp_plan_analysis import covariates_step, exclusions_step, model_step, scaling_step
from marp_plan_measures import norms_step, religiosity_step, wellbeing_step

from borges.analysis.schemas import PlannerOutput

ESTIMAND = {
    1: (
        "Standardised regression coefficient of self-reported well-being on religiosity "
        "across 10,535 participants in 24 countries; positive means more religious people "
        "report more well-being. The option space is seeded from the analytic choices the "
        "120 MARP teams documented."
    ),
    2: (
        "Standardised coefficient of the religiosity by perceived-cultural-norms interaction "
        "on self-reported well-being across 10,535 participants in 24 countries; positive means "
        "religiosity goes with more well-being where religion is seen as more important. "
        "The option space is seeded from the analytic choices the 120 MARP teams documented."
    ),
}


def plan_dict(rq: int) -> dict:
    c = team_choice_counts()
    steps = [religiosity_step(c), wellbeing_step(c)]
    if rq == 2:
        steps.append(norms_step(c))
    steps += [exclusions_step(c), covariates_step(c), scaling_step(c), model_step(c)]
    return {"estimand": ESTIMAND[rq], "steps": steps}


def validated_planner(rq: int) -> PlannerOutput:
    return PlannerOutput.model_validate(plan_dict(rq))
