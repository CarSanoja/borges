from __future__ import annotations

VERDICTS = {
    "skin_tone.rater1_only": (
        0.72,
        "Using one of the two blind raters is a documented choice among the crowdsourced teams; "
        "it discards information from the second rater but keeps the same exposure.",
    ),
    "skin_tone.rater2_only": (
        0.72,
        "The mirror of the rater 1 choice: a single rater scale, with the caveat that this rater "
        "scored darker on average.",
    ),
    "skin_tone.extremes_only": (
        0.62,
        "Contrasting clearly light with clearly dark players is a recognised sensitivity check, "
        "but it discards the middle of the scale and changes the sample.",
    ),
    "exclusions.rated_frequent_refs": (
        0.72,
        "Referees seen in few dyads give unstable rates, so requiring a minimum is a standard "
        "precision rule; the cut-off is a judgement.",
    ),
    "covariates.physique": (
        0.88,
        "Height, weight and position are pre-treatment player characteristics that relate to "
        "carding; adjusting for them is standard.",
    ),
    "covariates.full": (
        0.82,
        "League country is a pre-treatment context variable; adjusting for it alongside physique "
        "is a common specification among the research teams.",
    ),
    "model.poisson_offset": (
        0.85,
        "Red cards are rare counts over varying exposure, so a Poisson model with a log-games "
        "offset is the textbook alternative to the binomial model.",
    ),
    "model.binomial_cluster": (
        0.86,
        "A player appears in many dyads, so clustering the errors by player corrects the "
        "uncertainty without changing the estimand.",
    ),
}
