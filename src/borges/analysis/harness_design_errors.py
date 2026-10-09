"""Messages of a model step whose design the harness refuses.

fertility_vote on 7 October, run 31: the model refused a design whose fertility indicator was all
zeros and suggested dummy coding; the indicator arrived all zeros because the first step passed on
an empty cycle-day column. A dead column that is already constant in the data the model step
receives is named as the earlier steps' fault, in the words that send the smoke run to repair them.

A clinic run (r_20261009T034108_7e3b1d) adjusted a protocol introduced in July for every arrival
month: the month dummies after July add up to the exposure, the message suggested drop_first,
and three repairs kept the dummies. When the covariates rebuild the exposure, they are named.
"""

from __future__ import annotations

from borges.analysis.model_spec.render_design import INPUT_FAULT

DESIGN_ERRORS_SOURCE = """
    def _rebuilding(scaled, names, exposure, frame_columns):
        if exposure is None or scaled.shape[1] < 2:
            return []
        others = [i for i in range(scaled.shape[1]) if i != exposure]
        target = scaled[:, exposure]
        coef = _np.linalg.lstsq(scaled[:, others], target, rcond=None)[0]
        if _np.linalg.norm(scaled[:, others] @ coef - target) > 1e-6:
            return []
        own = _term_of(str(names[exposure]), frame_columns)
        return sorted(
            {
                _term_of(str(names[i]), frame_columns)
                for i, c in zip(others, coef)
                if abs(c) > 1e-6 and str(names[i]).lower() not in ("const", "intercept")
            }
            - {own}
        )

    def _rebuilt_error(design):
        return (
            "the exposure " + repr(str(design["exposure"] or "of the model")) + " is an exact"
            + " linear combination of the covariates " + repr(design["rebuilt_by"][:8])
            + " and the intercept: together they rebuild it, as month or period dummies do when"
            + " the exposure starts at a date for every unit, so its effect cannot be separated"
            + " from them. Leave those covariates out of this model (drop their columns before"
            + " fitting) instead of dropping levels, and name each one with this reason in the"
            + " returned dict's 'note', for example {'note': "
            + repr(str(design["rebuilt_by"][0]) + " left out: it rebuilds the exposure")
            + "}; a numeric time trend can stay."
            + " Columns: " + repr(design["names"][:20])
        )

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
        if design["columns"] > design.get("observations", design["columns"]):
            return (
                "the model's design has " + str(design["columns"]) + " columns but only "
                + str(design["observations"]) + " rows reach the model, so it cannot be"
                + " estimated: a column with a value for almost every row (an identifier, a date"
                + " or a free-text answer) must not be dummy-coded or put in C(...), and the steps"
                + " before the model must not leave fewer rows than the model has terms."
                + " Columns: " + repr(design["names"][:20])
            )
        if design.get("rebuilt_by"):
            return _rebuilt_error(design)
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
