"""Covariates a model step is given and leaves out of its fit.

A free-code model one-hot encoded the whole frame and then kept the columns named in
ctx['covariates']; every categorical covariate had become job_admin, job_blue-collar and so on, so
none was found, and the model ran unadjusted while the report said it adjusted for six covariates
(bank, 4323c97). A covariate the earlier step lists that is a column of the frame, appears in no
term of the fitted model and is not named in the step's note (dropped with a reason) fails the
step. An option that says it uses no covariates, a covariate with one value in the frame (nothing
to adjust for) and a design with unnamed columns (x1, x2: nothing to match) are not checked.
"""

from __future__ import annotations

COVARIATES_SOURCE = """
    def _uses_covariate(column, terms):
        import re as _re

        pattern = _re.compile("(?<![A-Za-z0-9_])" + _re.escape(column) + "(?![A-Za-z0-9])")
        return column in terms or any(pattern.search(term) for term in terms)

    def _ignored_covariates(design, ctx, frame, note):
        import re as _re

        listed = ctx.get("covariates")
        terms = list(design["terms"])
        if not __ADJUSTS__ or not isinstance(listed, list):
            return []
        if any(_re.fullmatch("x[0-9]+", term) for term in terms):
            return []
        names = [str(c) for c in listed if str(c) in frame.columns and str(c) not in note]
        return [
            c for c in names
            if frame[c].nunique(dropna=True) > 1 and not _uses_covariate(c, terms)
        ]

    def _ignored_error(names, design):
        return (
            "ctx['covariates'] lists " + ", ".join(names) + ", but no term of the fitted model is"
            + " built from them, so the analysis is not adjusted for them; one-hot encode the"
            + " covariate columns themselves (pd.get_dummies(df[covariates], drop_first=True,"
            + " dtype=float)) or write C(column) in a formula. Model columns: "
            + repr(design["names"][:20])
        )
"""
