from __future__ import annotations

SKIN_MEAN = """import pandas as pd


def apply(df, ctx):
    out = df.copy()
    out["skin_tone"] = out[["rater1", "rater2"]].mean(axis=1, skipna=False)
    return out
"""

SKIN_RATER1 = """import pandas as pd


def apply(df, ctx):
    out = df.copy()
    out["skin_tone"] = out["rater1"]
    return out
"""

SKIN_RATER2 = """import pandas as pd


def apply(df, ctx):
    out = df.copy()
    out["skin_tone"] = out["rater2"]
    return out
"""

SKIN_EXTREMES = """import pandas as pd


def apply(df, ctx):
    out = df.copy()
    out["skin_tone"] = out[["rater1", "rater2"]].mean(axis=1, skipna=False)
    keep = (out["skin_tone"] <= 0.25) | (out["skin_tone"] >= 0.75)
    return out[keep].copy()
"""

EXCL_RATED = """import pandas as pd


def apply(df, ctx):
    keep = df["rater1"].notna() & df["rater2"].notna() & df["skin_tone"].notna()
    return df[keep].copy()
"""

EXCL_FREQUENT = """import pandas as pd


def apply(df, ctx):
    keep = df["rater1"].notna() & df["rater2"].notna() & df["skin_tone"].notna()
    out = df[keep].copy()
    dyads = out.groupby("refNum")["refNum"].transform("size")
    return out[dyads >= 22].copy()
"""

COV_NONE = """import pandas as pd


def apply(df, ctx):
    ctx["covariates"] = []
    return df
"""

COV_PHYSIQUE = """import pandas as pd


def apply(df, ctx):
    ctx["covariates"] = ["height", "weight", "position"]
    return df
"""

COV_FULL = """import pandas as pd


def apply(df, ctx):
    ctx["covariates"] = ["position", "leagueCountry", "height", "weight"]
    return df
"""

COV_ADV_BIAS = """import pandas as pd


def apply(df, ctx):
    ctx["covariates"] = ["position", "leagueCountry", "height", "weight", "meanIAT", "meanExp"]
    return df
"""

_DESIGN = """    covariates = list(ctx.get("covariates", []))
    needed = ["skin_tone", "games", "redCards", "playerShort"] + covariates
    data = df.dropna(subset=needed).copy()
    data["playerShort"] = data["playerShort"].astype(str)
    numeric = [c for c in covariates if pd.api.types.is_numeric_dtype(data[c])]
    categorical = [c for c in covariates if c not in numeric]
    parts = [data[["skin_tone"]].astype(float), data[numeric].astype(float)]
    if categorical:
        parts.append(
            pd.get_dummies(data[categorical].astype(str), drop_first=True, dtype=float)
        )
    exog = sm.add_constant(pd.concat(parts, axis=1), has_constant="add")
"""

MODEL_BINOMIAL = (
    """import numpy as np
import pandas as pd
import statsmodels.api as sm


def estimate(df, ctx):
"""
    + _DESIGN
    + """    successes = data["redCards"].clip(upper=data["games"]).astype(float)
    endog = pd.concat([successes, data["games"].astype(float) - successes], axis=1)
    fit = sm.GLM(endog, exog, family=sm.families.Binomial()).fit()
    low, high = fit.conf_int().loc["skin_tone"]
    return {
        "estimate": float(np.exp(fit.params["skin_tone"])),
        "ci_low": float(np.exp(low)),
        "ci_high": float(np.exp(high)),
        "p_value": float(fit.pvalues["skin_tone"]),
        "n": int(len(data)),
        "extra": {"log_odds": float(fit.params["skin_tone"])},
    }
"""
)

MODEL_POISSON = (
    """import numpy as np
import pandas as pd
import statsmodels.api as sm


def estimate(df, ctx):
"""
    + _DESIGN
    + """    offset = np.log(data["games"].astype(float))
    fit = sm.GLM(
        data["redCards"].astype(float), exog, family=sm.families.Poisson(), offset=offset
    ).fit()
    low, high = fit.conf_int().loc["skin_tone"]
    return {
        "estimate": float(np.exp(fit.params["skin_tone"])),
        "ci_low": float(np.exp(low)),
        "ci_high": float(np.exp(high)),
        "p_value": float(fit.pvalues["skin_tone"]),
        "n": int(len(data)),
        "extra": {"log_rate_ratio": float(fit.params["skin_tone"])},
    }
"""
)

MODEL_CLUSTER = (
    """import numpy as np
import pandas as pd
import statsmodels.api as sm


def estimate(df, ctx):
"""
    + _DESIGN
    + """    successes = data["redCards"].clip(upper=data["games"]).astype(float)
    endog = pd.concat([successes, data["games"].astype(float) - successes], axis=1)
    groups = pd.factorize(data["playerShort"])[0]
    fit = sm.GLM(endog, exog, family=sm.families.Binomial()).fit(
        cov_type="cluster", cov_kwds={"groups": groups}
    )
    low, high = fit.conf_int().loc["skin_tone"]
    return {
        "estimate": float(np.exp(fit.params["skin_tone"])),
        "ci_low": float(np.exp(low)),
        "ci_high": float(np.exp(high)),
        "p_value": float(fit.pvalues["skin_tone"]),
        "n": int(len(data)),
        "extra": {"log_odds": float(fit.params["skin_tone"])},
    }
"""
)

EXCL_LOW_IAT = """import pandas as pd


def apply(df, ctx):
    keep = df["rater1"].notna() & df["rater2"].notna() & df["skin_tone"].notna()
    out = df[keep].copy()
    return out[out["meanIAT"] < out["meanIAT"].median()].copy()
"""

BASE_OPTIONS: dict[str, str] = {
    "skin_tone.mean_raters": SKIN_MEAN,
    "skin_tone.rater1_only": SKIN_RATER1,
    "skin_tone.rater2_only": SKIN_RATER2,
    "skin_tone.extremes_only": SKIN_EXTREMES,
    "exclusions.rated_only": EXCL_RATED,
    "exclusions.rated_frequent_refs": EXCL_FREQUENT,
    "covariates.none": COV_NONE,
    "covariates.physique": COV_PHYSIQUE,
    "covariates.full": COV_FULL,
    "model.binomial_glm": MODEL_BINOMIAL,
    "model.poisson_offset": MODEL_POISSON,
    "model.binomial_cluster": MODEL_CLUSTER,
}

ADVERSARY_OPTIONS: dict[str, str] = {
    "covariates.adv_full_plus_bias": COV_ADV_BIAS,
    "exclusions.adv_low_iat_referees_only": EXCL_LOW_IAT,
}
