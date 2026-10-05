from __future__ import annotations

import numpy as np
import pandas as pd
import statsmodels.api as sm

from borges.analysis.model_spec.schema import ModelSpecOutput


def _design(spec: ModelSpecOutput, d: pd.DataFrame, covariates: list[str]) -> pd.DataFrame:
    x = pd.DataFrame({spec.exposure: d[spec.exposure].astype(float)})
    if spec.moderator:
        x[spec.moderator] = d[spec.moderator].astype(float)
        x["interaction"] = d[spec.exposure].astype(float) * d[spec.moderator].astype(float)
    for name in covariates:
        if pd.api.types.is_numeric_dtype(d[name]):
            x[name] = d[name].astype(float)
        else:
            dummies = pd.get_dummies(d[name].astype(str), drop_first=True, dtype=float)
            x = pd.concat([x, dummies.add_prefix(f"{name}_")], axis=1)
    return sm.add_constant(x, has_constant="add")


def _fit(spec: ModelSpecOutput, y, x, offset, d: pd.DataFrame):
    kwargs: dict = {"cov_type": spec.cov_type}
    if spec.cov_type == "cluster":
        kwargs["cov_kwds"] = {"groups": d[spec.cluster].astype("category").cat.codes.to_numpy()}
    extra = {"offset": offset} if offset is not None else {}
    if spec.family == "ols":
        return sm.OLS(y, x).fit(**kwargs)
    if spec.family == "logit":
        return sm.Logit(y, x).fit(disp=0, **kwargs)
    if spec.family == "poisson":
        return sm.GLM(y, x, family=sm.families.Poisson(), **extra).fit(**kwargs)
    nb2 = sm.NegativeBinomial(y, x, **extra).fit(method="newton", tol=1e-12, maxiter=500, disp=0)
    family = sm.families.NegativeBinomial(alpha=float(np.asarray(nb2.params)[-1]))
    return sm.GLM(y, x, family=family, **extra).fit(**kwargs)


def reference(spec: ModelSpecOutput, df: pd.DataFrame, ctx: dict) -> dict[str, float]:
    core = [c for c in (spec.outcome, spec.exposure, spec.moderator) if c]
    covariates = list(spec.covariates)
    if spec.covariates_from_ctx:
        covariates += list(ctx.get("covariates", []))
    covariates = [c for c in dict.fromkeys(covariates) if c not in core]
    used = core + [c for c in (spec.cluster, spec.offset_log) if c] + covariates
    d = df.dropna(subset=list(dict.fromkeys(used))).reset_index(drop=True)
    for name in spec.standardize:
        d[name] = (d[name] - d[name].mean()) / d[name].std()
    offset = np.log(d[spec.offset_log].astype(float)) if spec.offset_log else None
    x = _design(spec, d, covariates)
    fit = _fit(spec, d[spec.outcome].astype(float), x, offset, d)
    term = "interaction" if spec.moderator else spec.exposure
    low, high = np.asarray(fit.conf_int())[list(x.columns).index(term)]
    value = float(np.asarray(fit.params)[list(x.columns).index(term)])
    p = float(np.asarray(fit.pvalues)[list(x.columns).index(term)])
    if spec.report != "coefficient":
        value, low, high = float(np.exp(value)), float(np.exp(low)), float(np.exp(high))
    return {
        "estimate": value,
        "ci_low": float(low),
        "ci_high": float(high),
        "p_value": p,
        "n": len(d),
    }
