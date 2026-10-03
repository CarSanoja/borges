from __future__ import annotations

_HEAD = """import numpy as np
import pandas as pd


def apply(df, ctx):
    out = df.copy()
"""


def _apply(body: str) -> str:
    return _HEAD + body + "    return out\n"


STORMS = {
    "drop_top2": _apply('    out = out.drop(index=out.nlargest(2, "alldeaths").index)\n'),
    "keep_all": _apply(""),
    "drop_top1": _apply('    out = out.drop(index=out.nlargest(1, "alldeaths").index)\n'),
    "drop_over_100": _apply('    out = out[out["alldeaths"] <= 100]\n'),
}

ADVERSARY_STORMS = {
    "adv_drop_top3_damages": _apply(
        '    out = out.drop(index=out.nlargest(2, "alldeaths").index)\n'
        '    out = out.drop(index=out.nlargest(3, "ndam15").index)\n'
    ),
    "adv_pre_1979_only": _apply(
        '    out = out.drop(index=out.nlargest(2, "alldeaths").index)\n'
        '    out = out[out["year"] < 1979]\n'
    ),
}

FEMININITY = {
    "masfem": _apply(
        '    out["fem_x"] = out["masfem"].astype(float)\n    ctx["binary_fem"] = False\n'
    ),
    "female_binary": _apply(
        '    out["fem_x"] = out["gender_mf"].astype(float)\n    ctx["binary_fem"] = True\n'
    ),
    "masfem_mturk": _apply(
        '    out["fem_x"] = out["masfem_mturk"].astype(float)\n    ctx["binary_fem"] = False\n'
    ),
}

DAMAGES = {
    "linear_2015": _apply('    out["dam_x"] = out["ndam15"].astype(float)\n'),
    "log_2015": _apply('    out["dam_x"] = np.log(out["ndam15"].astype(float))\n'),
    "linear_2013": _apply('    out["dam_x"] = out["ndam"].astype(float)\n'),
}

STRENGTH = {
    "pressure": _apply('    out["str_x"] = -out["min"].astype(float)\n'),
    "wind": _apply('    out["str_x"] = out["wind"].astype(float)\n'),
    "category": _apply('    out["str_x"] = out["category"].astype(float)\n'),
}

INTERACTION = {
    "full": _apply('    ctx["interaction"] = "full"\n'),
    "damages_only": _apply('    ctx["interaction"] = "damages"\n'),
    "main_effect": _apply('    ctx["interaction"] = "none"\n'),
}

YEAR = {
    "none": _apply('    out["yr_x"] = 0.0\n    ctx["year_term"] = False\n'),
    "year_x_damages": _apply(
        '    out["yr_x"] = out["year"].astype(float)\n    ctx["year_term"] = True\n'
    ),
    "post1979_x_damages": _apply(
        '    out["yr_x"] = (out["year"] >= 1979).astype(float)\n    ctx["year_term"] = True\n'
    ),
}

_MODEL_HEAD = """import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy import stats


def estimate(df, ctx):
    need = ["fem_x", "dam_x", "str_x", "yr_x", "alldeaths", "gender_mf"]
    data = df.dropna(subset=need).copy()
    interaction = ctx["interaction"]
    year_term = bool(ctx["year_term"])
    z = {}
    for name in ("fem_x", "dam_x", "str_x", "yr_x"):
        spread = float(data[name].std())
        z[name] = (data[name].astype(float) - float(data[name].mean())) / (spread or 1.0)

    def row(fem, dam, strength, year):
        values = [1.0, fem, dam, strength]
        if interaction == "full":
            values.extend([fem * dam, fem * strength, fem * dam * strength, dam * strength])
        elif interaction == "damages":
            values.append(fem * dam)
        if year_term:
            values.extend([year, year * dam])
        return np.asarray(values, dtype=float)

    design = np.vstack(
        [
            row(f, d, s, y)
            for f, d, s, y in zip(
                z["fem_x"], z["dam_x"], z["str_x"], z["yr_x"], strict=True
            )
        ]
    )
    deaths = data["alldeaths"].astype(float).to_numpy()
    if ctx["binary_fem"]:
        raw_high, raw_low = 1.0, 0.0
    else:
        by_sex = data.groupby("gender_mf")["fem_x"].mean()
        raw_high = float(by_sex.loc[1])
        raw_low = float(by_sex.loc[0])
    spread = float(data["fem_x"].std()) or 1.0
    centre = float(data["fem_x"].mean())
    x_high = row((raw_high - centre) / spread, 0.0, 0.0, 0.0)
    x_low = row((raw_low - centre) / spread, 0.0, 0.0, 0.0)
"""

_MODEL_TAIL = """    level_high = float(np.exp(x_high @ beta))
    level_low = float(np.exp(x_low @ beta))
    gap = level_high - level_low
    grad = level_high * x_high - level_low * x_low
    se = float(np.sqrt(grad @ cov @ grad))
    p_value = float(2 * stats.norm.sf(abs(gap / se)))
    return {
        "estimate": float(gap),
        "ci_low": float(gap - 1.96 * se),
        "ci_high": float(gap + 1.96 * se),
        "p_value": p_value,
        "n": int(len(data)),
        "extra": {
            "predicted_masculine": level_low - SHIFT,
            "predicted_feminine": level_high - SHIFT,
        },
    }
"""

NEGBIN = (
    _MODEL_HEAD
    + """    with np.errstate(all="ignore"):
        poisson = sm.GLM(deaths, design, family=sm.families.Poisson()).fit(maxiter=500)
        start = np.append(np.asarray(poisson.params, dtype=float), 0.5)
        model = sm.NegativeBinomial(deaths, design)
        fit = model.fit(start_params=start, method="bfgs", maxiter=5000, disp=0)
        if not fit.mle_retvals["converged"]:
            fit = model.fit(start_params=fit.params, method="nm", maxiter=5000, disp=0)
    k = design.shape[1]
    beta = np.asarray(fit.params, dtype=float)[:k]
    cov = np.asarray(fit.cov_params(), dtype=float)[:k, :k]
"""
    + _MODEL_TAIL.replace("SHIFT", "0.0")
)

OLS_LOG1P = (
    _MODEL_HEAD
    + """    fit = sm.OLS(np.log1p(deaths), design).fit()
    beta = np.asarray(fit.params, dtype=float)
    cov = np.asarray(fit.cov_params(), dtype=float)
"""
    + _MODEL_TAIL.replace("SHIFT", "1.0")
)

MODELS = {"negbin": NEGBIN, "ols_log1p": OLS_LOG1P}

ADVERSARY_OPTIONS: dict[str, str] = {f"storms.{k}": v for k, v in ADVERSARY_STORMS.items()}

BASE_OPTIONS: dict[str, str] = {
    **{f"storms.{k}": v for k, v in STORMS.items()},
    **{f"femininity.{k}": v for k, v in FEMININITY.items()},
    **{f"damages.{k}": v for k, v in DAMAGES.items()},
    **{f"strength.{k}": v for k, v in STRENGTH.items()},
    **{f"interaction.{k}": v for k, v in INTERACTION.items()},
    **{f"year_control.{k}": v for k, v in YEAR.items()},
    **{f"model.{k}": v for k, v in MODELS.items()},
}
