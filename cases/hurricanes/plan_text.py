from __future__ import annotations

from plan_steps import PLANNER, SIMONSOHN

from borges.analysis.schemas import AdversaryOutput, JudgeOutput, PlannerOutput

ADVERSARY = {
    "proposals": [
        {
            "step_id": "storms",
            "id": "adv_drop_top3_damages",
            "label": "Also drop the three most damaging storms",
            "rationale": (
                "A handful of very costly storms can pull a fit with damage terms; trimming "
                "high-leverage points is a standard robustness check."
            ),
            "spec": "Drop the two deadliest storms, then the three highest ndam15 rows.",
            "source": SIMONSOHN,
        },
        {
            "step_id": "storms",
            "id": "adv_pre_1979_only",
            "label": "Only storms before 1979",
            "rationale": "Before 1979 every storm had a female name, so it isolates one regime.",
            "spec": "Drop the two deadliest storms, keep years < 1979.",
            "source": None,
        },
    ]
}

JUDGE = {
    "storms.adv_drop_top3_damages": {
        "defensibility": 0.7,
        "accepted": True,
        "reason": (
            "Trimming the highest-leverage storms is a recognised robustness check that keeps "
            "the population and the estimand, and the original critics raised it."
        ),
        "source": SIMONSOHN,
    },
    "storms.adv_pre_1979_only": {
        "defensibility": 0.3,
        "accepted": False,
        "reason": (
            "Restricting to one naming regime discards more than half the storms and changes "
            "what the contrast between feminine and masculine names means."
        ),
        "source": None,
    },
}


def validated_planner() -> PlannerOutput:
    return PlannerOutput.model_validate(PLANNER)


def validated_adversary() -> AdversaryOutput:
    return AdversaryOutput.model_validate(ADVERSARY)


def validated_judge(key: str) -> JudgeOutput:
    return JudgeOutput.model_validate(JUDGE[key])
