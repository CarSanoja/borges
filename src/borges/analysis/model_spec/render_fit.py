from __future__ import annotations

from borges.analysis.model_spec.render_design import design_term
from borges.analysis.model_spec.schema import ModelSpecOutput


def _fit_arguments(spec: ModelSpecOutput) -> str:
    if spec.cov_type == "cluster":
        return 'cov_type="cluster", cov_kwds={"groups": groups}'
    return f'cov_type="{spec.cov_type}"'


def _count_lines(spec: ModelSpecOutput, arguments: str) -> list[str]:
    offset = ", offset=offset" if spec.offset_log is not None else ""
    if spec.family == "poisson":
        return [
            f"    model = sm.GLM(endog, exog, family=sm.families.Poisson(){offset})",
            f"    fit = model.fit({arguments})",
        ]
    return [
        f"    pilot = sm.GLM(endog, exog, family=sm.families.Poisson(){offset}).fit()",
        "    mu = pilot.mu",
        "    alpha = max(float((((endog - mu) ** 2 - endog).sum()) / (mu**2).sum()), 1e-4)",
        "    family = sm.families.NegativeBinomial(alpha=alpha)",
        f"    model = sm.GLM(endog, exog, family=family{offset})",
        f"    fit = model.fit({arguments})",
    ]


def fit_lines(spec: ModelSpecOutput) -> list[str]:
    arguments = _fit_arguments(spec)
    lines = []
    if spec.offset_log is not None:
        lines.append(f"    offset = np.log(data[{spec.offset_log!r}].astype(float))")
    if spec.cov_type == "cluster":
        lines.append(f"    groups = pd.factorize(data[{spec.cluster!r}])[0]")
    if spec.family == "ols":
        lines += ["    model = sm.OLS(endog, exog)", f"    fit = model.fit({arguments})"]
    elif spec.family == "logit":
        lines += ["    model = sm.Logit(endog, exog)", f"    fit = model.fit(disp=0, {arguments})"]
    else:
        lines += _count_lines(spec, arguments)
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
        '        "extra": {"std_err": float(row["Std. Err."])},',
        "    }",
    ]


def result_lines(spec: ModelSpecOutput) -> list[str]:
    if spec.report == "marginal_effect":
        return _margeff_lines(spec)
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
        '        "extra": {"coefficient": value},',
        "    }",
    ]
