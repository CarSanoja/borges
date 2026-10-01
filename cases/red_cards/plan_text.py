from __future__ import annotations

from borges.analysis.schemas import AdversaryOutput, JudgeOutput, PlannerOutput

CITATION = "Silberzahn et al. (2018), Advances in Methods and Practices in Psychological Science"

ESTIMAND = (
    "Odds ratio of a red card per game comparing skin tone 1 (darkest) with skin tone 0 "
    "(lightest), estimated on player-referee dyads."
)

PLANNER = {
    "estimand": ESTIMAND,
    "steps": [
        {
            "id": "skin_tone",
            "title": "Measure skin tone",
            "kind": "feature",
            "description": "Two raters scored each player photo, 0 very light to 1 very dark.",
            "options": [
                {
                    "id": "mean_raters",
                    "label": "Mean of both raters",
                    "rationale": "Averaging two blind raters reduces rating noise.",
                    "spec": "skin_tone = mean(rater1, rater2); missing if either is missing.",
                    "is_default": True,
                    "source": CITATION,
                },
                {
                    "id": "rater1_only",
                    "label": "Rater 1 only",
                    "rationale": "A single rater avoids mixing two scoring styles.",
                    "spec": "skin_tone = rater1.",
                },
                {
                    "id": "rater2_only",
                    "label": "Rater 2 only",
                    "rationale": "Rater 2 scored darker on average, so this is the mirror check.",
                    "spec": "skin_tone = rater2.",
                },
                {
                    "id": "extremes_only",
                    "label": "Clearly light or clearly dark",
                    "rationale": "Dropping ambiguous mid-scale players sharpens the contrast.",
                    "spec": "Keep players whose mean rating is <= 0.25 or >= 0.75.",
                },
            ],
        },
        {
            "id": "exclusions",
            "title": "Choose which dyads to keep",
            "kind": "filter",
            "description": "Dyads are player-referee pairs; some players have no photo rating.",
            "options": [
                {
                    "id": "rated_only",
                    "label": "Rated players only",
                    "rationale": "Skin tone is undefined without both ratings.",
                    "spec": "Drop rows missing either rating.",
                    "is_default": True,
                },
                {
                    "id": "rated_frequent_refs",
                    "label": "Rated players, referees with 22+ dyads",
                    "rationale": "Referees seen in few dyads add noisy rates.",
                    "spec": "Drop unrated rows, then referees with fewer than 22 dyads.",
                },
            ],
        },
        {
            "id": "covariates",
            "title": "Adjust for context",
            "kind": "feature",
            "description": "Decide which player and league attributes enter the model.",
            "options": [
                {
                    "id": "none",
                    "label": "No covariates",
                    "rationale": "The raw contrast answers the question as asked.",
                    "spec": "covariates = [].",
                    "is_default": True,
                },
                {
                    "id": "physique",
                    "label": "Height, weight, position",
                    "rationale": "Defenders and heavier players are fouled and carded more.",
                    "spec": "covariates = [height, weight, position].",
                },
                {
                    "id": "full",
                    "label": "Physique plus league country",
                    "rationale": "Leagues differ in how strictly red cards are given.",
                    "spec": "covariates = [position, leagueCountry, height, weight].",
                },
            ],
        },
        {
            "id": "model",
            "title": "Fit the model",
            "kind": "model",
            "description": "Estimate the odds ratio of a red card per game.",
            "options": [
                {
                    "id": "binomial_glm",
                    "label": "Binomial GLM",
                    "rationale": "Red cards out of games is a binomial outcome.",
                    "spec": "GLM Binomial on (redCards, games - redCards); OR = exp(coef).",
                    "is_default": True,
                },
                {
                    "id": "poisson_offset",
                    "label": "Poisson GLM with log-games offset",
                    "rationale": "Red cards are rare counts over exposure.",
                    "spec": "GLM Poisson with offset log(games); reports the rate ratio.",
                },
                {
                    "id": "binomial_cluster",
                    "label": "Binomial GLM, player-clustered errors",
                    "rationale": "A player appears in many dyads, so rows are not independent.",
                    "spec": "Binomial GLM with cluster-robust standard errors by player.",
                },
            ],
        },
    ],
}

ADVERSARY = {
    "proposals": [
        {
            "step_id": "covariates",
            "id": "adv_full_plus_bias",
            "label": "Full set plus referee-country bias scores",
            "rationale": (
                "Referee-country implicit and explicit bias could confound who is carded; "
                "several teams in the published study adjusted for them."
            ),
            "spec": "covariates = [position, leagueCountry, height, weight, meanIAT, meanExp].",
            "source": CITATION,
        },
        {
            "step_id": "exclusions",
            "id": "adv_low_iat_referees_only",
            "label": "Only referees from low implicit-bias countries",
            "rationale": "Cleaner comparison among referees with less measured bias.",
            "spec": "Drop unrated rows, keep referees whose country meanIAT is below median.",
            "source": None,
        },
    ]
}

JUDGE = {
    "covariates.adv_full_plus_bias": {
        "defensibility": 0.72,
        "accepted": True,
        "reason": (
            "Adjusting for referee-country bias scores is a standard confounder control, keeps "
            "the population and the estimand unchanged, and was used by published analysts."
        ),
        "source": CITATION,
    },
    "exclusions.adv_low_iat_referees_only": {
        "defensibility": 0.35,
        "accepted": False,
        "reason": (
            "Keeping only low-bias referees changes the population and tests the question where "
            "bias is least likely, so a null there says nothing about referees in general."
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
