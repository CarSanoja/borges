"""Messages of a model step whose design the harness refuses."""

from __future__ import annotations

DESIGN_ERRORS_SOURCE = """
    def _intercept_error(design):
        return (
            "the " + str(design["no_intercept"]) + " model has no intercept: no column of its"
            + " design is constant, so the fit is forced through the origin and the coefficient"
            + " of the exposure absorbs the missing constant; add one with"
            + " sm.add_constant(X, has_constant='add') or use a formula, which adds it."
            + " Columns: " + repr(design["names"][:20])
        )

    def _design_error(design):
        cond = design["condition"]
        if design["rank"] < design["columns"] or design["dead"]:
            dead = ", all-zero columns " + repr(design["dead"][:8]) if design["dead"] else ""
            detail = (
                "rank " + str(design["rank"]) + " of " + str(design["columns"]) + " columns"
                + dead
            )
        else:
            detail = "condition number " + format(cond, ".3g") + " above __DESIGN_CONDITION_LIMIT__"
        wide = ""
        if design["columns"] > __DESIGN_WIDE_COLUMNS__:
            wide = (
                " The design has " + str(design["columns"]) + " columns: a categorical with"
                + " hundreds of levels (an identifier such as a player, referee, user or country)"
                + " must not be dummy-coded; cluster the errors on it or aggregate to that unit."
            )
        return (
            "the model's design matrix is rank-deficient or collinear (" + detail
            + "): collinear columns are redundant and make the standard errors meaningless;"
            + " typical cause: dummy columns for every level of a categorical plus an intercept"
            + " (use pd.get_dummies(..., drop_first=True, dtype=float))."
            + wide
            + " Columns: " + repr(design["names"][:20])
        )
"""
