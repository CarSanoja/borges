from __future__ import annotations

import pandas as pd
from marp_reference import load_coding, load_teams

ALL_REL = frozenset(f"rel_{i}" for i in range(1, 10))
SEVEN_REL = frozenset(f"rel_{i}" for i in (1, 2, 5, 6, 7, 8, 9))
ALL_WB = frozenset(
    ["wb_gen_1", "wb_gen_2", "wb_soc_1", "wb_soc_2", "wb_soc_3"]
    + [f"wb_phys_{i}" for i in range(1, 8)]
    + [f"wb_psych_{i}" for i in range(1, 7)]
)
SUBSCALE_MEANS = frozenset({"wb_phys_mean", "wb_psych_mean", "wb_soc_mean"})
FREE_TEXT = [
    "AnalyticalApproach",
    "StatsDetail",
    "OtherSteps1",
    "OtherSteps2",
    "DeviateExclusions",
    "DeviateModel",
    "DeviateDV",
    "DeviateIV",
    "Covariates1",
    "Covariates2",
    "Comments",
]


def _sets(series: pd.Series) -> pd.Series:
    return series.map(lambda s: frozenset(x.strip() for x in str(s).split(";") if x.strip()))


def _mentions(text: pd.Series, pattern: str) -> int:
    return int(text.str.contains(pattern, regex=True).sum())


def team_choice_counts() -> dict[str, int]:
    coding = load_coding()
    rq1 = coding[coding.iv_rq1 != ""]
    rq2 = coding[coding.iv_rq2 != ""]
    iv, dv = _sets(rq1.iv_rq1), _sets(rq1.dv_rq1)
    model = rq1.statisitcal_model.str.lower()
    covs = rq1.cov_rq1.str.lower()
    teams = load_teams()
    text = teams[FREE_TEXT].fillna("").astype(str).agg(" ".join, axis=1).str.lower()
    return {
        "coded": len(rq1),
        "free_text": len(teams),
        "rel_all9": int((iv == ALL_REL).sum()),
        "rel_self_id": int((iv == frozenset({"rel_3"})).sum()),
        "rel_seven": int((iv == SEVEN_REL).sum()),
        "rel_importance": int((iv == frozenset({"rel_8", "rel_9"})).sum()),
        "wb_overall": int((dv == frozenset({"wb_overall_mean"})).sum()),
        "wb_no_sexual": int((dv == ALL_WB - {"wb_soc_3"}).sum()),
        "wb_subscale_means": int((dv >= SUBSCALE_MEANS).sum()),
        "wb_general_alone": int((dv == frozenset({"wb_gen_1", "wb_gen_2"})).sum()),
        "wb_general_in_sets": int(dv.map(lambda s: "wb_gen_1" in s).sum()),
        "cov_none": int((covs == "none").sum()),
        "cov_demographics": int(covs.map(lambda s: "age" in s and "ses" in s).sum()),
        "cov_gdp": int(covs.str.contains("gdp").sum()),
        "model_multilevel": int(model.str.contains("multilevel|mixed|hierarch").sum()),
        "model_linear": int((model == "linear regression").sum()),
        "norms_items": int(rq2.iv_rq2.str.contains("cnorm").sum()),
        "norms_total": len(rq2),
        "mention_attention": _mentions(text, "attention"),
        "mention_country_level": _mentions(text, "country[- ]level|aggregat"),
        "mention_within_country": _mentions(text, "within[- ]country"),
        "mention_standardi": _mentions(text, "standardi"),
        "mention_random_slope": _mentions(text, "random slope"),
        "mention_random_intercept": _mentions(text, "random intercept"),
    }
