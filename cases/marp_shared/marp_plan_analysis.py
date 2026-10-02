from __future__ import annotations

from marp_plan_core import opt as _opt


def exclusions_step(c):
    return {
        "id": "exclusions",
        "title": "Choose which participants to keep",
        "kind": "filter",
        "description": "Some respondents failed the attention check embedded in the survey.",
        "options": [
            _opt(
                "all_participants",
                "All participants",
                "No data-driven exclusion; the full 10,535 respondents.",
                "No rows dropped.",
                "the default in the data release.",
                True,
            ),
            _opt(
                "attention_check_passed",
                "Attention check passed only",
                "Inattentive responding adds noise to every item.",
                "Keep attention_check == 1.",
                f"{c['mention_attention']} of {c['free_text']} team reports mention the "
                "attention check.",
            ),
        ],
    }


def covariates_step(c):
    n = c["coded"]
    return {
        "id": "covariates",
        "title": "Adjust for context",
        "kind": "feature",
        "description": "Choose which participant and country attributes enter the model.",
        "options": [
            _opt(
                "none",
                "No covariates",
                "The raw association answers the question as asked.",
                "covariates = [].",
                f"{c['cov_none']} of {n} teams adjusted for nothing.",
                True,
            ),
            _opt(
                "demographics",
                "Age, gender, SES, education",
                "Demographics relate to both religiosity and well-being.",
                "covariates = [age, gender, ses, education]; complete cases.",
                f"{c['cov_demographics']} of {n} teams adjusted for age and SES, "
                "usually with gender and education.",
            ),
            _opt(
                "demographics_gdp",
                "Demographics plus country GDP",
                "Wealth differs across the 24 countries.",
                "covariates = [age, gender, ses, education, gdp_scaled]; complete cases.",
                f"{c['cov_gdp']} of {n} teams adjusted for GDP.",
            ),
        ],
    }


def scaling_step(c):
    return {
        "id": "scaling",
        "title": "Standardise the variables",
        "kind": "transform",
        "description": "Convert variables to z-scores so the coefficient is a standardised beta.",
        "options": [
            _opt(
                "global_z",
                "Z-scores over the whole sample",
                "The usual standardised beta; keeps between-country differences.",
                "y, x (and m) = global z-scores.",
                f"{c['mention_standardi']} of {c['free_text']} team reports mention standardising.",
                True,
            ),
            _opt(
                "within_country_z",
                "Centred within country",
                "Isolates the within-country relation; 'with and between country centering'.",
                "y and x centred on their country mean and scaled; m stays a global z-score.",
                f"{c['mention_within_country']} of {c['free_text']} team reports "
                "mention within-country centring.",
            ),
        ],
    }


def model_step(c):
    n = c["coded"]
    return {
        "id": "model",
        "title": "Fit the model",
        "kind": "model",
        "description": "Participants are nested in 24 countries; the model "
        "family decides how that is handled.",
        "options": [
            _opt(
                "multilevel_intercept",
                "Multilevel model, random country intercept",
                "The most common choice: respondents nested in countries.",
                "mixedlm y ~ terms, groups = country.",
                f"{c['model_multilevel']} of {n} teams fit a multilevel, mixed or "
                f"hierarchical model; {c['mention_random_intercept']} reports mention "
                "random intercepts.",
                True,
            ),
            _opt(
                "ols_pooled",
                "Pooled OLS, robust errors",
                "Ignores country structure, as a simple regression does.",
                "OLS y ~ terms with HC3 standard errors.",
                f"{c['model_linear']} of {n} teams fit a plain linear regression.",
            ),
            _opt(
                "ols_country_fe",
                "OLS with country fixed effects",
                "Absorbs country differences without distributional assumptions.",
                "OLS y ~ terms + C(country), HC3 standard errors.",
                "a fixed-effects specification of the same teams' linear models.",
            ),
            _opt(
                "multilevel_slope",
                "Multilevel model, random country slopes",
                "Lets the religiosity slope differ by country.",
                "mixedlm y ~ terms, groups = country, random slope on x.",
                f"{c['mention_random_slope']} of {c['free_text']} team reports mention "
                "random slopes.",
            ),
        ],
    }
