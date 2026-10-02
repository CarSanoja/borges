from __future__ import annotations

from marp_apply_code import (
    COV_DEMOGRAPHICS,
    COV_DEMOGRAPHICS_GDP,
    COV_NONE,
    EXCL_ALL,
    EXCL_ATTENTION,
    NORMS_COUNTRY,
    NORMS_INDIVIDUAL,
    REL_7,
    REL_9,
    REL_IMPORTANCE,
    REL_SELF_ID,
    SCALE_GLOBAL,
    SCALE_WITHIN,
    WB_GENERAL,
    WB_NO_SEXUAL,
    WB_OVERALL,
    WB_SUBSCALES,
)

_HEAD = """import numpy as np
import pandas as pd
import statsmodels.formula.api as smf


def estimate(df, ctx):
    data = df.copy()
    data["country"] = data["country"].astype(str)
    covariates = list(ctx.get("covariates", []))
"""

_TAIL = """    low, high = fit.conf_int().loc[term]
    return {
        "estimate": float(fit.params[term]),
        "ci_low": float(low),
        "ci_high": float(high),
        "p_value": float(fit.pvalues[term]),
        "n": int(fit.nobs),
    }
"""

_RHS = {
    1: '    terms = ["x"] + covariates\n    term = "x"\n',
    2: '    terms = ["x", "m", "x:m"] + covariates\n    term = "x:m"\n',
}

_CONVERGED = (
    '    if not fit.converged:\n        raise ValueError("the mixed model did not converge")\n'
)

_FIT = {
    "ols_pooled": '    formula = "y ~ " + " + ".join(terms)\n'
    '    fit = smf.ols(formula, data).fit(cov_type="HC3")\n',
    "ols_country_fe": '    formula = "y ~ " + " + ".join(terms) + " + C(country)"\n'
    '    fit = smf.ols(formula, data).fit(cov_type="HC3")\n',
    "multilevel_intercept": '    formula = "y ~ " + " + ".join(terms)\n'
    '    model = smf.mixedlm(formula, data, groups=data["country"])\n'
    '    fit = model.fit(reml=True, method=["powell", "lbfgs"])\n' + _CONVERGED,
    "multilevel_slope": '    formula = "y ~ " + " + ".join(terms)\n'
    '    model = smf.mixedlm(formula, data, groups=data["country"], re_formula="~x")\n'
    '    fit = model.fit(reml=True, method=["powell", "lbfgs"])\n' + _CONVERGED,
}


def model_code(rq: int, model_id: str) -> str:
    return _HEAD + _RHS[rq] + _FIT[model_id] + _TAIL


RELIGIOSITY = {
    "mean_9_items": REL_9,
    "mean_7_items": REL_7,
    "self_identification": REL_SELF_ID,
    "importance_items": REL_IMPORTANCE,
}
WELLBEING = {
    "overall_mean": WB_OVERALL,
    "items_without_sexual_satisfaction": WB_NO_SEXUAL,
    "mean_of_subscales": WB_SUBSCALES,
    "general_items": WB_GENERAL,
}
NORMS = {"individual_perception": NORMS_INDIVIDUAL, "country_mean": NORMS_COUNTRY}
EXCLUSIONS = {"all_participants": EXCL_ALL, "attention_check_passed": EXCL_ATTENTION}
COVARIATES = {
    "none": COV_NONE,
    "demographics": COV_DEMOGRAPHICS,
    "demographics_gdp": COV_DEMOGRAPHICS_GDP,
}
SCALING = {"global_z": SCALE_GLOBAL, "within_country_z": SCALE_WITHIN}
MODELS = ["multilevel_intercept", "ols_pooled", "ols_country_fe", "multilevel_slope"]


def option_codes(rq: int) -> dict[str, str]:
    groups = {
        "religiosity": RELIGIOSITY,
        "wellbeing": WELLBEING,
        "exclusions": EXCLUSIONS,
        "covariates": COVARIATES,
        "scaling": SCALING,
        **({"norms": NORMS} if rq == 2 else {}),
    }
    codes = {f"{step}.{oid}": code for step, opts in groups.items() for oid, code in opts.items()}
    codes.update({f"model.{m}": model_code(rq, m) for m in MODELS})
    return codes


def step_order(rq: int) -> list[str]:
    head = ["religiosity", "wellbeing"] + (["norms"] if rq == 2 else [])
    return [*head, "exclusions", "covariates", "scaling", "model"]


def defaults(rq: int) -> dict[str, str]:
    base = {
        "religiosity": "mean_9_items",
        "wellbeing": "overall_mean",
        "exclusions": "all_participants",
        "covariates": "none",
        "scaling": "global_z",
        "model": "multilevel_intercept",
    }
    if rq == 2:
        base["norms"] = "individual_perception"
    return {s: base[s] for s in step_order(rq)}


def option_ids(rq: int) -> dict[str, list[str]]:
    groups = {
        "religiosity": list(RELIGIOSITY),
        "wellbeing": list(WELLBEING),
        "norms": list(NORMS),
        "exclusions": list(EXCLUSIONS),
        "covariates": list(COVARIATES),
        "scaling": list(SCALING),
        "model": MODELS,
    }
    return {s: groups[s] for s in step_order(rq)}
