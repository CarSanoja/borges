"""A random-intercept linear model: statsmodels MixedLM, restricted maximum likelihood, one
intercept per level of the grouping column. The reported estimate is the fixed effect of the
design term, the exposure or the exposure x moderator interaction, with the Wald interval and
p-value of the fit.
"""

from __future__ import annotations

from borges.analysis.model_spec.schema import ModelSpecOutput

FEW_GROUPS_HEAD = "the random intercept needs at least 2 groups in the column "
FEW_GROUPS_TAIL = (
    ", and the rows left after dropping the incomplete ones fall in "
    "{found}: a variance between groups cannot be estimated"
)


def mixed_lines(spec: ModelSpecOutput) -> list[str]:
    column = str(spec.random_intercept)
    tail = FEW_GROUPS_TAIL.replace("{found}", "' + str(len(set(groups))) + '")
    return [
        f"    groups = pd.factorize(data[{column!r}])[0]",
        "    if len(set(groups)) < 2:",
        f"        raise ValueError({FEW_GROUPS_HEAD!r} + {column!r} + '{tail}')",
        "    model = sm.MixedLM(endog, exog, groups=groups)",
        "    fit = model.fit()",
    ]
