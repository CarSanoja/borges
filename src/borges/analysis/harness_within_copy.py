"""A regressor that is the reported term minus its group means, or the other way round.

An audit run (r_20261009T101518_df1978) asked whether more review hours lower restatements. An
adversary option, "Adjust for manager fixed effects via demeaning", put manager_review_hours minus
its manager's mean among the covariates while the model still reported manager_review_hours. With
both, y = a*x + b*(x - mean) = (a + b)*(x - mean) + a*mean, so the reported coefficient a is the
effect of the managers' means: the comparison between managers the option meant to remove. The run
reported it as the minimal flip. A model with two regressors whose difference is constant within
groups, one of them summing to zero in each group, fails the step.
"""

from __future__ import annotations

WITHIN_MIN_ROWS = 20

WITHIN_COPY_SOURCE = """
    def _within_copy(x, found):
        target = x[:, found]
        for j in range(x.shape[1]):
            column = x[:, j]
            if j == found or _np.std(column) == 0:
                continue
            levels, groups = _np.unique(_np.round(target - column, 9), return_inverse=True)
            if len(levels) < 2 or len(levels) > len(target) / 2:
                continue
            counts = _np.bincount(groups)
            for centred in (column, target):
                means = _np.bincount(groups, weights=centred) / counts
                if _np.all(_np.abs(means) <= 1e-6 * max(1.0, float(_np.abs(centred).max()))):
                    return j
        return None

    def _check_within_copy(estimate):
        if not __DESIGN_CHECK__ or not isinstance(estimate, (int, float)):
            return
        for _, exog, names, model_id in reversed(_designs):
            if model_id in _helpers:
                continue
            found = _exposure_index(_fits.get(model_id), estimate, len(names))
            if found is None:
                continue
            try:
                x = _np.asarray(exog, dtype=float)
            except Exception:
                return
            if x.ndim != 2 or x.shape[0] < __WITHIN_MIN_ROWS__ or not _np.isfinite(x).all():
                return
            j = _within_copy(x, found)
            if j is None:
                return
            raise ValueError(
                "the model has both " + str(names[found]) + " and " + str(names[j]) + ", which"
                + " differ by a value that is constant within groups (one is the other minus its"
                + " group means): with both, the reported coefficient compares the groups' means,"
                + " between groups, not rows within a group, so it is not a fixed-effects"
                + " estimate; to adjust for the groups, put the group column among the covariates"
                + " as categories (fixed-effect dummies) and keep one copy of the exposure"
            )
"""
