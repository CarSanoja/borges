"""Messages of a model step whose design the harness refuses.

fertility_vote on 7 October, run 31: the model refused a design whose fertility indicator was all
zeros and suggested dummy coding; the indicator arrived all zeros because the first step passed on
an empty cycle-day column. A dead column that is already constant in the data the model step
receives is named as the earlier steps' fault, in the words that send the smoke run to repair them.
"""

from __future__ import annotations

from borges.analysis.model_spec.render_design import INPUT_FAULT

DESIGN_ERRORS_SOURCE = """
    def _intercept_error(design):
        return (
            "the " + str(design["no_intercept"]) + " model has no intercept: no column of its"
            + " design is constant, so the fit is forced through the origin and the coefficient"
            + " of the exposure absorbs the missing constant; add one with"
            + " sm.add_constant(X, has_constant='add') or use a formula, which adds it."
            + " Columns: " + repr(design["names"][:20])
        )

    def _arrived_constant(design, df):
        names = [c for c in design["dead"] if df is not None and c in df.columns]
        try:
            return [c for c in names if df[c].nunique(dropna=True) <= 1]
        except Exception:
            return []

    def _design_error(design, df=None):
        cond = design["condition"]
        constant = _arrived_constant(design, df)
        if constant:
            return (
                "the model's design has all-zero columns " + repr(constant[:8]) + " that arrive"
                + " with the same value in every row in the data this step receives: __FAULT__"
                + " produced a constant, so the model cannot estimate their effect."
                + " Columns: " + repr(design["names"][:20])
            )
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
""".replace("__FAULT__", INPUT_FAULT)
