"""The negative binomial dispersion is fitted by maximum likelihood as R's glm.nb does, and the
model is then fitted at that alpha. The derivative of the profile log-likelihood in theta =
1/alpha is the score of theta at the means of the GLM fitted at that theta, so its root is found
with Brent's method, each step a warm-started GLM fit; when the score is still positive at alpha
= exp(-10) there is no overdispersion and alpha stays at that bound. A moment estimator used
until 4cf0663 gave alpha 0.23 for the hurricanes flip at a491fe1 where maximum likelihood gives
1.67, and the flip was significant only at the smaller alpha. Maximising the profile likelihood
by its values took about 30 cold fits and timed out in ConTree on 115,000 red_cards rows at
7ec07d9, and the values are flat to rounding near the optimum, which stalled a glm.nb-style
alternation.
"""

from __future__ import annotations

from borges.analysis.model_spec.render_count_margins import count_margin_lines
from borges.analysis.model_spec.render_design import design_term
from borges.analysis.model_spec.schema import GEE_FAMILIES, GROUPED, ModelSpecOutput

SCALED_OUTCOME = "outcome z-scored with the predictors: "
NB_UNCONVERGED = (
    "the negative binomial dispersion has no maximum-likelihood estimate in the range searched, "
    "up to an alpha of about 148: the counts are more dispersed than the model can describe"
)
ALPHA_BOUNDS = (-10.0, 5.0)
AT_BOUND = ", at the lower bound: no overdispersion, so the model is in effect a Poisson model"


def _fit_arguments(spec: ModelSpecOutput) -> str:
    if spec.cov_type == "cluster":
        return 'cov_type="cluster", cov_kwds={"groups": groups}'
    return f'cov_type="{spec.cov_type}"'


def _count_lines(spec: ModelSpecOutput, arguments: str) -> list[str]:
    offset = ", offset=offset" if spec.offset_log is not None else ""
    if spec.family in ("poisson", "quasipoisson"):
        scale = 'scale="X2", ' if spec.family == "quasipoisson" else ""
        return [
            f"    model = sm.GLM(endog, exog, family=sm.families.Poisson(){offset})",
            f"    fit = model.fit({scale}{arguments})",
        ]
    return [
        "    from scipy.optimize import brentq",
        "    from scipy.special import digamma",
        "",
        "    def slope(log_theta):",
        "        theta = float(np.exp(log_theta))",
        "        nb.family = sm.families.NegativeBinomial(alpha=1.0 / theta)",
        "        pilot = nb.fit(start_params=warm['start'])",
        "        warm['start'] = pilot.params",
        "        mu = np.asarray(pilot.mu)",
        "        terms = digamma(counts + theta) - digamma(theta) + np.log(theta / (theta + mu))",
        "        return float((terms + (mu - counts) / (theta + mu)).sum())",
        "",
        "    counts = np.asarray(endog, dtype=float)",
        "    warm = {'start': None}",
        f"    nb = sm.GLM(endog, exog, family=sm.families.NegativeBinomial(alpha=1.0){offset})",
        f"    bounds = {ALPHA_BOUNDS!r}",
        "    if slope(-bounds[0]) > 0:",
        "        log_alpha = bounds[0]",
        "    elif slope(-bounds[1]) < 0:",
        f"        raise ValueError({NB_UNCONVERGED!r})",
        "    else:",
        "        log_alpha = -brentq(slope, -bounds[1], -bounds[0], xtol=1e-10)",
        "    alpha = float(np.exp(log_alpha))",
        "    fitted = f'negative binomial alpha {alpha:.4g} by maximum likelihood'",
        "    if log_alpha < bounds[0] + 0.1:",
        f"        fitted += {AT_BOUND!r}",
        "    note += ('; ' if note else '') + fitted",
        "    family = sm.families.NegativeBinomial(alpha=alpha)",
        f"    model = sm.GLM(endog, exog, family=family{offset})",
        f"    fit = model.fit({arguments})",
    ]


def _gee_lines(spec: ModelSpecOutput) -> list[str]:
    family = GEE_FAMILIES[str(spec.family)]
    offset = ", offset=offset" if spec.offset_log is not None else ""
    return [
        "    model = sm.GEE(",
        f"        endog, exog, groups=groups, family=sm.families.{family}(),",
        f"        cov_struct=sm.cov_struct.Exchangeable(){offset}",
        "    )",
        "    fit = model.fit(maxiter=100)",
    ]


def fit_lines(spec: ModelSpecOutput) -> list[str]:
    arguments = _fit_arguments(spec)
    lines = []
    if spec.offset_log is not None:
        lines.append(f"    offset = np.log(data[{spec.offset_log!r}].astype(float))")
    if spec.cov_type in GROUPED:
        lines.append(f"    groups = pd.factorize(data[{spec.cluster!r}])[0]")
    if spec.cov_type == "gee":
        lines += _gee_lines(spec)
    elif spec.family == "ols":
        lines += ["    model = sm.OLS(endog, exog)", f"    fit = model.fit({arguments})"]
    elif spec.family == "logit":
        lines += ["    model = sm.Logit(endog, exog)", f"    fit = model.fit(disp=0, {arguments})"]
    else:
        lines += _count_lines(spec, arguments)
    if spec.outcome in spec.standardize:
        lines.append(f"    note += ('; ' if note else '') + {SCALED_OUTCOME + str(spec.outcome)!r}")
    return lines


def _margeff_lines(spec: ModelSpecOutput) -> list[str]:
    return [
        f"    term = {design_term(spec)!r}",
        '    effects = fit.get_margeff(at="overall", method="dydx", dummy=True).summary_frame()',
        "    row = effects.loc[term]",
        "    return {",
        '        "estimate": float(row["dy/dx"]),',
        '        "ci_low": float(row["Conf. Int. Low"]),',
        '        "ci_high": float(row["Cont. Int. Hi."]),',
        '        "p_value": float(row["Pr(>|z|)"]),',
        '        "n": int(len(data)),',
        '        "note": note,',
        '        "extra": {"std_err": float(row["Std. Err."])},',
        "    }",
    ]


def result_lines(spec: ModelSpecOutput) -> list[str]:
    if spec.report == "marginal_effect":
        return _margeff_lines(spec) if spec.family == "logit" else count_margin_lines(spec)
    ratio = spec.report != "coefficient"
    lines = [
        f"    term = {design_term(spec)!r}",
        "    ci = fit.conf_int()",
        "    low, high = (float(v) for v in ci.loc[term])",
        "    value = float(fit.params[term])",
        "    p_value = float(fit.pvalues[term])",
    ]
    if not ratio:
        return [
            *lines,
            "    return {",
            '        "estimate": value,',
            '        "ci_low": low,',
            '        "ci_high": high,',
            '        "p_value": p_value,',
            '        "n": int(len(data)),',
            '        "note": note,',
            "    }",
        ]
    return [
        *lines,
        "    return {",
        '        "estimate": float(np.exp(value)),',
        '        "ci_low": float(np.exp(low)),',
        '        "ci_high": float(np.exp(high)),',
        '        "p_value": p_value,',
        '        "n": int(len(data)),',
        '        "note": note,',
        '        "extra": {"coefficient": value},',
        "    }",
    ]
