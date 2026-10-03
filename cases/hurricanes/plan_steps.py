from __future__ import annotations

JUNG = "Jung et al. (2014), PNAS 111(24)"
SIMONSOHN = "Simonsohn, Simmons and Nelson (2020), Nature Human Behaviour 4"

ESTIMAND = (
    "Additional deaths from a hurricane with a feminine rather than a masculine name, "
    "estimated as the difference in predicted deaths between the two name groups with the "
    "other predictors held at their sample means."
)


def _option(option_id, label, rationale, spec, default=False, source=None):
    return {
        "id": option_id,
        "label": label,
        "rationale": rationale,
        "spec": spec,
        "is_default": default,
        "source": source,
    }


PLANNER = {
    "estimand": ESTIMAND,
    "steps": [
        {
            "id": "storms",
            "title": "Choose which storms to analyse",
            "kind": "filter",
            "description": "Two storms account for most deaths; analysts differ on keeping them.",
            "options": [
                _option(
                    "drop_top2",
                    "Drop the two deadliest storms",
                    "The original analysis set aside the two extreme-death storms.",
                    "Remove the two rows with the highest alldeaths.",
                    True,
                    JUNG,
                ),
                _option(
                    "keep_all",
                    "Keep every storm",
                    "Nothing in the question calls for discarding data.",
                    "Use all 94 storms.",
                ),
                _option(
                    "drop_top1",
                    "Drop only the deadliest storm",
                    "A milder trim that removes the single most extreme observation.",
                    "Remove the one row with the highest alldeaths.",
                ),
                _option(
                    "drop_over_100",
                    "Drop storms with more than 100 deaths",
                    "Critics of the original paper argued that very deadly storms should go.",
                    "Keep only storms with alldeaths <= 100.",
                    source=SIMONSOHN,
                ),
            ],
        },
        {
            "id": "femininity",
            "title": "Measure name femininity",
            "kind": "feature",
            "description": "The data hold a coder rating, a second rating and a binary flag.",
            "options": [
                _option(
                    "masfem",
                    "Coder rating (1 to 11)",
                    "A graded rating keeps the information in the names.",
                    "fem = masfem.",
                    True,
                    JUNG,
                ),
                _option(
                    "female_binary",
                    "Female versus male name",
                    "The binary reading is the plain meaning of the claim.",
                    "fem = gender_mf (1 female, 0 male).",
                ),
                _option(
                    "masfem_mturk",
                    "Online-panel rating (1 to 11)",
                    "A second, independent set of raters scored the same names.",
                    "fem = masfem_mturk.",
                ),
            ],
        },
        {
            "id": "damages",
            "title": "Measure property damage",
            "kind": "feature",
            "description": "Damage is heavily right-skewed and exists in two inflation bases.",
            "options": [
                _option(
                    "linear_2015",
                    "Damage in 2015 dollars",
                    "Complete for every storm and on the scale analysts usually report.",
                    "dam = ndam15.",
                    True,
                ),
                _option(
                    "log_2015",
                    "Log of damage in 2015 dollars",
                    "A log scale tames the skew in damage.",
                    "dam = ln(ndam15).",
                    source=SIMONSOHN,
                ),
                _option(
                    "linear_2013",
                    "Damage in 2013 dollars",
                    "The measure used in the original paper.",
                    "dam = ndam; storms with missing ndam drop out.",
                    source=JUNG,
                ),
            ],
        },
        {
            "id": "strength",
            "title": "Measure storm strength",
            "kind": "feature",
            "description": "Three landfall measures describe the intensity of a storm.",
            "options": [
                _option(
                    "pressure",
                    "Minimum pressure",
                    "Pressure at landfall is a direct physical measure of intensity.",
                    "str = -min, so that a higher value means a stronger storm.",
                    True,
                    JUNG,
                ),
                _option(
                    "wind",
                    "Maximum wind speed",
                    "Wind speed is the other common intensity measure.",
                    "str = wind.",
                ),
                _option(
                    "category",
                    "Saffir-Simpson category",
                    "A standard five-level scale for storm strength.",
                    "str = category.",
                ),
            ],
        },
        {
            "id": "interaction",
            "title": "Choose the functional form for femininity",
            "kind": "feature",
            "description": "Femininity can act on deaths alone or through damage and strength.",
            "options": [
                _option(
                    "full",
                    "Interact with damage and strength",
                    "Femininity may matter more for damaging, intense storms.",
                    "Include fem*dam, fem*str, fem*dam*str and dam*str.",
                    True,
                    JUNG,
                ),
                _option(
                    "damages_only",
                    "Interact with damage only",
                    "A simpler interaction with the damage measure alone.",
                    "Include fem*dam.",
                ),
                _option(
                    "main_effect",
                    "Main effect only",
                    "The most direct reading of the claim, with no interaction.",
                    "No interaction terms.",
                ),
            ],
        },
        {
            "id": "year_control",
            "title": "Control for the era of the storm",
            "kind": "feature",
            "description": "Reporting and preparedness changed over six decades.",
            "options": [
                _option(
                    "none",
                    "No time control",
                    "The original analysis did not adjust for the year.",
                    "No year terms.",
                    True,
                ),
                _option(
                    "year_x_damages",
                    "Year and year by damage",
                    "Allows deaths per unit of damage to drift over time.",
                    "Add year and year*dam.",
                    source=SIMONSOHN,
                ),
                _option(
                    "post1979_x_damages",
                    "Post-1979 indicator and its interaction with damage",
                    "Names alternated between sexes from 1979, so era is entangled with name.",
                    "Add post1979 and post1979*dam.",
                    source=SIMONSOHN,
                ),
            ],
        },
        {
            "id": "model",
            "title": "Fit the model",
            "kind": "model",
            "description": "Deaths are counts with a heavy right tail.",
            "options": [
                _option(
                    "negbin",
                    "Negative binomial regression",
                    "Overdispersed counts call for a negative binomial model.",
                    "NB2 log-link GLM, dispersion by maximum likelihood.",
                    True,
                    JUNG,
                ),
                _option(
                    "ols_log1p",
                    "Linear model on log(deaths + 1)",
                    "A common alternative that is easy to inspect.",
                    "OLS of ln(alldeaths + 1); effects back-transformed to deaths.",
                    source=SIMONSOHN,
                ),
            ],
        },
    ],
}
