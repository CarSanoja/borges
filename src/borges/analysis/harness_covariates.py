"""Covariates a model step is given and leaves out of its fit.

A free-code model one-hot encoded the whole frame and then kept the columns named in
ctx['covariates']; every categorical covariate had become job_admin, job_blue-collar and so on, so
none was found, and the model ran unadjusted while the report said it adjusted for six covariates
(bank, 4323c97). A covariate the earlier step lists that is a column of the frame, appears in no
term of the fitted model and is not named in the step's note (dropped with a reason) fails the
step. An option that says it uses no covariates, a covariate with one value in the frame (nothing
to adjust for) and a design with unnamed columns (x1, x2: nothing to match) are not checked.

`pd.get_dummies(df["gender"])` names its columns by the levels (other, woman), not by the column.
Every rejection in the recordings up to 0b92e6c was such a model, adjusted for gender, country or
leagueCountry through level-named dummies (marp_norms at 068fa85 and 0b92e6c, red_cards at d29a189,
where it cost the default logit). A design column named after a level of the covariate counts as
built from it.

A clinic run (r_20261009T035043_992430) listed arrival_month for a protocol introduced in July at
every site: the months after July add up to the exposure, so no model can hold both, and the
repairs went back and forth between this check and the rank check. A covariate whose levels by
themselves rebuild the exposure in the frame is left out with a note, as lm leaves out an aliased
column, and the report says so.
"""

from __future__ import annotations

from borges.analysis.model_spec.render_alias import REBUILT_NOTE

COVARIATES_SOURCE = """
    def _uses_covariate(column, terms):
        import re as _re

        pattern = _re.compile("(?<![A-Za-z0-9_])" + _re.escape(column) + "(?![A-Za-z0-9])")
        return column in terms or any(pattern.search(term) for term in terms)

    def _level_named(column, frame, names):
        try:
            levels = {str(v) for v in frame[column].dropna().unique()[:1000]}
        except Exception:
            return False
        return any(str(name) in levels for name in names)

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
            if frame[c].nunique(dropna=True) > 1
            and not _uses_covariate(c, terms)
            and not _level_named(c, frame, design.get("names") or [])
        ]

    def _encoded(series):
        if _pd.api.types.is_numeric_dtype(series):
            return series.astype(float).to_frame()
        return _pd.get_dummies(series.astype(str), drop_first=True, dtype=float)

    def _rebuilds_exposure(column, design, frame):
        exposure = design.get("exposure")
        if not exposure or exposure not in frame.columns or column == exposure:
            return False
        try:
            data = frame[[column, exposure]].dropna()
            x = _np.column_stack([_np.ones(len(data)), _encoded(data[column]).to_numpy()])
            y = _encoded(data[exposure]).to_numpy()
        except Exception:
            return False
        if y.shape[0] < 2 or y.shape[1] == 0 or float(_np.std(y)) == 0.0:
            return False
        coef = _np.linalg.lstsq(x, y, rcond=None)[0]
        return bool(_np.abs(x @ coef - y).max() < 1e-8)

    def _left_out(design, ctx, frame, trace):
        ignored = _ignored_covariates(design, ctx, frame, trace["note"])
        rebuilt = [c for c in ignored if _rebuilds_exposure(c, design, frame)]
        if rebuilt:
            left = __REBUILT_NOTE__ + ", ".join(rebuilt)
            trace["note"] = (left + "; " + trace["note"] if trace["note"] else left)[:500]
        return [c for c in ignored if c not in rebuilt]

    def _ignored_error(names, design):
        return (
            "ctx['covariates'] lists " + ", ".join(names) + ", but no term of the fitted model is"
            + " built from them, so the analysis is not adjusted for them; one-hot encode the"
            + " covariate columns themselves (pd.get_dummies(df[covariates], drop_first=True,"
            + " dtype=float)) or write C(column) in a formula. Model columns: "
            + repr(design["names"][:20])
        )
""".replace("__REBUILT_NOTE__", repr(REBUILT_NOTE))
