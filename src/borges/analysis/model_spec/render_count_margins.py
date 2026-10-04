"""The average marginal effect of a count model: additional events per unit of the exposure.

With a log link dmu_i/dx = b * mu_i, so the average is b * mean(mu). Its standard error comes from
the delta method on the fitted covariance: the gradient in the exposure's coefficient is mean(mu)
plus b * mean(mu * x_exposure), and in every other coefficient b * mean(mu * x_j). This is what
"additional deaths per unit" means, without the baseline exp(intercept) that is meaningless when a
covariate cannot be zero.
"""

from __future__ import annotations

from borges.analysis.model_spec.render_design import design_term
from borges.analysis.model_spec.schema import ModelSpecOutput


def count_margin_lines(spec: ModelSpecOutput) -> list[str]:
    return [
        "    from math import erfc, sqrt",
        f"    term = {design_term(spec)!r}",
        "    mu = np.asarray(fit.mu, dtype=float)",
        "    slope = float(fit.params[term])",
        "    value = slope * float(mu.mean())",
        "    matrix = exog.to_numpy(dtype=float)",
        "    gradient = slope * (mu[:, None] * matrix).mean(axis=0)",
        "    gradient[list(exog.columns).index(term)] += float(mu.mean())",
        "    covariance = np.asarray(fit.cov_params(), dtype=float)",
        "    se = float(np.sqrt(gradient @ covariance @ gradient))",
        "    p_value = float(erfc(abs(value / se) / sqrt(2.0))) if se > 0 else 1.0",
        "    return {",
        '        "estimate": value,',
        '        "ci_low": value - 1.959963984540054 * se,',
        '        "ci_high": value + 1.959963984540054 * se,',
        '        "p_value": p_value,',
        '        "n": int(len(data)),',
        '        "note": note,',
        '        "extra": {"std_err": se, "coefficient": slope},',
        "    }",
    ]
