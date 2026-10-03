from __future__ import annotations

from pathlib import Path

from borges.analysis.schemas import JudgeOutput, NarratorOutput, PlannerOutput
from borges.bench.scripted_fixtures import write_plan_fixtures

_APPLY = "import pandas as pd\n\n\ndef apply(df, ctx):\n"
_DESIGN = """import pandas as pd
import statsmodels.api as sm


def estimate(df, ctx):
    covariates = list(ctx.get("covariates", []))
    data = df.dropna(subset=["beauty", "eval", *covariates]).copy()
    numeric = [c for c in covariates if pd.api.types.is_numeric_dtype(data[c])]
    categorical = [c for c in covariates if c not in numeric]
    parts = [data[["beauty"]].astype(float), data[numeric].astype(float)]
    if categorical:
        parts.append(pd.get_dummies(data[categorical].astype(str), drop_first=True, dtype=float))
    exog = sm.add_constant(pd.concat(parts, axis=1), has_constant="add")
    outcome = data["eval"].astype(float)
"""
_TAIL = """    low, high = fit.conf_int().loc["beauty"]
    return {
        "estimate": float(fit.params["beauty"]),
        "ci_low": float(low),
        "ci_high": float(high),
        "p_value": float(fit.pvalues["beauty"]),
        "n": int(len(data)),
    }
"""


def _cov(names: list[str]) -> str:
    return _APPLY + f'    ctx["covariates"] = {names!r}\n    return df\n'


CODES = {
    "sample.all": _APPLY + "    return df.copy()\n",
    "sample.min_students_10": _APPLY + '    return df[df["students"] >= 10].copy()\n',
    "sample.multi_credit_only": _APPLY + '    return df[df["credits"] == "more"].copy()\n',
    "sample.adv_tenured_only": _APPLY + '    return df[df["tenure"] == "yes"].copy()\n',
    "controls.none": _cov([]),
    "controls.instructor": _cov(["gender", "minority", "age"]),
    "controls.full": _cov(["gender", "minority", "age", "credits", "division", "native", "tenure"]),
    "controls.adv_full_plus_size": _cov(
        ["gender", "minority", "age", "credits", "division", "native", "tenure", "allstudents"]
    ),
    "model.ols": _DESIGN + "    fit = sm.OLS(outcome, exog).fit()\n" + _TAIL,
    "model.ols_cluster_prof": _DESIGN
    + '    fit = sm.OLS(outcome, exog).fit(\n        cov_type="cluster", '
    + 'cov_kwds={"groups": pd.factorize(data["prof"])[0]}\n    )\n'
    + _TAIL,
    "model.wls_allstudents": _DESIGN
    + '    fit = sm.WLS(outcome, exog, weights=data["allstudents"].astype(float)).fit()\n'
    + _TAIL,
}


def _option(option_id, label, rationale, spec, default=False):
    return {
        "id": option_id,
        "label": label,
        "rationale": rationale,
        "spec": spec,
        "is_default": default,
        "source": None,
    }


PLANNER = {
    "estimand": "Change in the mean course evaluation score per one-unit increase in the "
    "instructor beauty rating.",
    "steps": [
        {
            "id": "sample",
            "title": "Choose which courses to keep",
            "kind": "filter",
            "description": "Some courses have very few respondents or are one-credit electives.",
            "options": [
                _option("all", "All courses", "No reason to discard data.", "Use every row.", True),
                _option(
                    "min_students_10",
                    "Courses with at least 10 respondents",
                    "Averages over few students are noisy.",
                    "Keep rows with students >= 10.",
                ),
                _option(
                    "multi_credit_only",
                    "Multi-credit courses only",
                    "One-credit electives differ from regular courses.",
                    "Keep rows with credits == 'more'.",
                ),
            ],
        },
        {
            "id": "controls",
            "title": "Adjust for instructor and course traits",
            "kind": "feature",
            "description": "Beauty may correlate with other instructor and course traits.",
            "options": [
                _option("none", "No controls", "The raw association.", "covariates = [].", True),
                _option(
                    "instructor",
                    "Instructor traits",
                    "Gender, minority status and age relate to evaluations.",
                    "covariates = [gender, minority, age].",
                ),
                _option(
                    "full",
                    "Instructor and course traits",
                    "Course level, credits, language and tenure also matter.",
                    "covariates = instructor traits + credits, division, native, tenure.",
                ),
            ],
        },
        {
            "id": "model",
            "title": "Fit the model",
            "kind": "model",
            "description": "Scores are bounded averages and instructors teach many courses.",
            "options": [
                _option(
                    "ols", "Ordinary least squares", "The standard linear model.", "OLS.", True
                ),
                _option(
                    "ols_cluster_prof",
                    "OLS, instructor-clustered errors",
                    "The same instructor appears in several rows.",
                    "OLS with cluster-robust errors by prof.",
                ),
                _option(
                    "wls_allstudents",
                    "Weighted least squares by enrolment",
                    "Larger classes give more reliable averages.",
                    "WLS weighted by allstudents.",
                ),
            ],
        },
    ],
}
ADVERSARY = {
    "proposals": [
        {
            "step_id": "controls",
            "id": "adv_full_plus_size",
            "label": "Full controls plus class size",
            "rationale": "Large classes tend to score lower and may differ in who teaches them.",
            "spec": "covariates = full set + allstudents.",
            "source": None,
        },
        {
            "step_id": "sample",
            "id": "adv_tenured_only",
            "label": "Tenured instructors only",
            "rationale": "Isolates one career stage.",
            "spec": "Keep rows with tenure == 'yes'.",
            "source": None,
        },
    ]
}
VERDICTS = {
    "sample.min_students_10": (0.7, "A respondent floor is a standard precision rule."),
    "sample.multi_credit_only": (0.7, "One-credit electives are a different kind of course."),
    "controls.instructor": (0.85, "Instructor traits are standard confounder controls."),
    "controls.full": (0.82, "Course traits are pre-treatment context."),
    "model.ols_cluster_prof": (0.86, "Clustering by instructor corrects the uncertainty."),
    "model.wls_allstudents": (0.7, "Enrolment weights are a common precision adjustment."),
}
ADVERSARY_JUDGES = {
    "controls.adv_full_plus_size": JudgeOutput(
        defensibility=0.7,
        accepted=True,
        reason="Class size is a plausible confounder.",
        source=None,
    ),
    "sample.adv_tenured_only": JudgeOutput(
        defensibility=0.3,
        accepted=False,
        reason="Restricting to tenured staff changes the population.",
        source=None,
    ),
}


def write_fixtures(directory: Path) -> None:
    write_plan_fixtures(
        directory,
        PlannerOutput.model_validate(PLANNER),
        CODES,
        VERDICTS,
        ADVERSARY,
        ADVERSARY_JUDGES,
        NarratorOutput(
            narrative="Scripted narrative for the benchmark plumbing check.", caveats=[]
        ),
    )
