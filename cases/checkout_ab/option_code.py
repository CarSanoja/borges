from __future__ import annotations

KEEP_ALL = """import pandas as pd


def apply(df, ctx):
    ctx["internal_traffic"] = "keep_all"
    return df
"""

EXCLUDE_INTERNAL = """import pandas as pd


def apply(df, ctx):
    ctx["internal_traffic"] = "exclude_internal"
    return df[~df["is_internal"]].reset_index(drop=True)
"""

BOT_NONE = """import pandas as pd


def apply(df, ctx):
    ctx["bot_filter"] = "none"
    return df
"""

BOT_MIN_2S = """import pandas as pd


def apply(df, ctx):
    ctx["bot_filter"] = "min_2s"
    return df[df["session_seconds"] >= 2.0].reset_index(drop=True)
"""

BOT_ENGAGED = """import pandas as pd


def apply(df, ctx):
    ctx["bot_filter"] = "adv_engaged_only"
    return df[df["session_seconds"] >= 30.0].reset_index(drop=True)
"""

NOVELTY_ALL = """import pandas as pd


def apply(df, ctx):
    ctx["novelty_window"] = "all_days"
    return df
"""

NOVELTY_DROP_3 = """import pandas as pd


def apply(df, ctx):
    ctx["novelty_window"] = "drop_first_3_days"
    return df[df["day"] >= 3].reset_index(drop=True)
"""

UNIT_SESSIONS = """import pandas as pd


def apply(df, ctx):
    ctx["unit"] = "sessions"
    return df
"""

UNIT_FIRST = """import pandas as pd


def apply(df, ctx):
    ctx["unit"] = "first_session_per_user"
    ordered = df.sort_values(["day", "session_id"], kind="mergesort")
    first = ordered.drop_duplicates(subset="user_id", keep="first")
    return first.sort_values("session_id").reset_index(drop=True)
"""

TWO_PROP_Z = """import math

import pandas as pd
from scipy import stats


def estimate(df, ctx):
    treated = df.loc[df["variant"] == "treatment", "converted"]
    control = df.loc[df["variant"] == "control", "converted"]
    n_t, n_c = len(treated), len(control)
    p_t, p_c = float(treated.mean()), float(control.mean())
    diff = p_t - p_c
    se = math.sqrt(p_t * (1 - p_t) / n_t + p_c * (1 - p_c) / n_c)
    pooled = (treated.sum() + control.sum()) / (n_t + n_c)
    se_null = math.sqrt(pooled * (1 - pooled) * (1 / n_t + 1 / n_c))
    p_value = 2 * (1 - stats.norm.cdf(abs(diff) / se_null))
    z = stats.norm.ppf(0.975)
    return {
        "estimate": diff,
        "ci_low": (diff - z * se),
        "ci_high": (diff + z * se),
        "p_value": float(p_value),
        "n": int(n_t + n_c),
        "extra": {"rate_treatment": 100 * p_t, "rate_control": 100 * p_c},
    }
"""

LOGIT_PLATFORM = """import pandas as pd
import statsmodels.formula.api as smf


def estimate(df, ctx):
    data = df.assign(treatment=(df["variant"] == "treatment").astype(int))
    fit = smf.logit("converted ~ treatment + C(platform)", data=data).fit(disp=False)
    margins = fit.get_margeff(at="overall", method="dydx", dummy=True).summary_frame()
    row = margins.loc["treatment"]
    return {
        "estimate": float(row["dy/dx"]),
        "ci_low": float(row["Conf. Int. Low"]),
        "ci_high": float(row["Cont. Int. Hi."]),
        "p_value": float(row["Pr(>|z|)"]),
        "n": int(fit.nobs),
        "extra": {"log_odds": float(fit.params["treatment"])},
    }
"""

OLS_CLUSTER = """import pandas as pd
import statsmodels.formula.api as smf


def estimate(df, ctx):
    data = df.assign(treatment=(df["variant"] == "treatment").astype(int))
    fit = smf.ols("converted ~ treatment", data=data).fit(
        cov_type="cluster", cov_kwds={"groups": data["user_id"]}
    )
    low, high = fit.conf_int().loc["treatment"]
    return {
        "estimate": float(fit.params["treatment"]),
        "ci_low": float(low),
        "ci_high": float(high),
        "p_value": float(fit.pvalues["treatment"]),
        "n": int(fit.nobs),
        "extra": {"n_clusters": float(data["user_id"].nunique())},
    }
"""

CODES: dict[str, str] = {
    "internal_traffic.keep_all": KEEP_ALL,
    "internal_traffic.exclude_internal": EXCLUDE_INTERNAL,
    "bot_filter.none": BOT_NONE,
    "bot_filter.min_2s": BOT_MIN_2S,
    "bot_filter.adv_engaged_only": BOT_ENGAGED,
    "novelty_window.all_days": NOVELTY_ALL,
    "novelty_window.drop_first_3_days": NOVELTY_DROP_3,
    "unit.sessions": UNIT_SESSIONS,
    "unit.first_session_per_user": UNIT_FIRST,
    "model.two_prop_z": TWO_PROP_Z,
    "model.logit_platform": LOGIT_PLATFORM,
    "model.adv_ols_cluster_user": OLS_CLUSTER,
}
