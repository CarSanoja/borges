"""Result checks that need the model that reports the estimate, run inside every model step.

A marp_norms WLS option at c83e4c2 reported n as the rows it was given (10,195) while its formula
dropped the rows with a missing covariate and fitted 10,170: n is the rows the model used. The
same option left the outcome in its raw units under a decision rule that reads a standardised
coefficient, which the template path z-scores; with the rescaled product term it reported 0.0747
where the consistent estimate was 0.034.

An A/B run on revenue per user (r_20261009T022441_66dcfd) summed each user's revenue, merged the
total back onto every session and fitted 21,624 session rows for 15,000 users: each user counted
once per session and the run said SHIP (p < 0.001) where one row per user gives p = 0.07. When the
outcome and the exposure are both constant within an identifier the fitted rows repeat, the rows
are copies of one unit, and the step fails so the repair fits one row per unit.

An audit run (r_20261009T083215_3c1abc) read the effect of review hours on the probability of a
restatement from a logit coefficient and its alternative from a probit one; the two scales differ
by about 1.6, and the summary called the gap the effect "roughly halving". Under a rule that reads
a probability, a Logit, Probit or binomial GLM coefficient fails the step.
"""

from __future__ import annotations

LINEAR_MODELS = ("OLS", "WLS", "GLS")
UNIT_SD = (0.9, 1.1)
MODEL_ROWS_NOTE = "n is the rows the model was fitted on; the code reported the rows it was given"

_SOURCE = """
    def _use_model_rows(frame, estimate, result, trace):
        if not __DESIGN_CHECK__:
            return
        for _, model_id in _reporting_models(estimate):
            endog, _ = _model_endog(_endogs.get(model_id))
            index = getattr(endog, "index", None)
            if index is None or result["n"] != len(frame) or len(index) >= len(frame):
                return
            if not index.isin(frame.index).all():
                return
            note = __MODEL_ROWS_NOTE__ + " (" + str(result["n"]) + ")"
            result["n"] = int(len(index))
            trace["note"] = (note + "; " + trace["note"] if trace["note"] else note)[:500]
            return

    def _check_copied_units(frame, design, result):
        if not __DESIGN_CHECK__ or not design:
            return
        outcome, exposure = design.get("outcome"), design.get("exposure")
        if outcome not in frame.columns or exposure not in frame.columns:
            return
        import re as _re

        n = int(result["n"])
        for column in frame.columns:
            name = str(column).lower()
            if column in (outcome, exposure) or not _re.search(r"(^|_)id$|[a-z]id$", name):
                continue
            ids = frame[column]
            k = int(ids.nunique(dropna=True))
            if k < 2 or n < k + max(3, int(0.01 * n)) or len(frame) != n:
                continue
            groups = frame.groupby(column, dropna=True)
            if (groups[outcome].nunique(dropna=False) > 1).any():
                continue
            if (groups[exposure].nunique(dropna=False) > 1).any():
                continue
            unit = repr(str(column))
            raise ValueError(
                "the model fits " + str(n) + " rows for " + str(k) + " distinct " + unit
                + " values, and " + repr(str(outcome)) + " and " + repr(str(exposure))
                + " are the same on every row of a " + unit + ": the rows are copies of one"
                + " unit, so each counts once per row; fit one row per " + unit
                + " (data = df.drop_duplicates(" + unit + ")) or aggregate with"
                + " groupby(...).agg(...) instead of merging the totals back"
            )

    def _check_probability_scale(estimate):
        if not (__DESIGN_CHECK__ and __PROBABILITY__):
            return
        for name, model_id in _reporting_models(estimate):
            family = getattr(_endogs.get(model_id), "family", None)
            link = type(getattr(family, "link", None)).__name__.lower()
            binomial = type(family).__name__ == "Binomial" and link != "identity"
            if name not in ("Logit", "Probit") and not binomial:
                return
            scale = "z" if "probit" in (name + link).lower() else "log-odds"
            raise ValueError(
                "the decision rule reads a change in a probability, but the estimate is the "
                + name + " coefficient, on the " + scale + " scale: it is no probability, and a"
                + " logit and a probit coefficient differ by about 1.6 on the same data. Report"
                + " the average marginal effect: row ="
                + " fit.get_margeff(at='overall').summary_frame().loc[<exposure>], with"
                + " row['dy/dx'], row['Conf. Int. Low'], row['Cont. Int. Hi.'] and"
                + " row['Pr(>|z|)']"
            )

    def _check_standardised_outcome(estimate):
        if not (__DESIGN_CHECK__ and __STANDARDISED__):
            return
        for name, model_id in _reporting_models(estimate):
            if name not in __LINEAR_MODELS__:
                return
            endog, _ = _model_endog(_endogs.get(model_id))
            try:
                values = _np.asarray(endog, dtype=float).ravel()
            except Exception:
                return
            if values.size < 3 or not _np.isfinite(values).all():
                return
            sd = float(_np.std(values, ddof=1))
            if __UNIT_SD__[0] <= sd <= __UNIT_SD__[1]:
                return
            columns = list(getattr(endog, "columns", []))
            label = getattr(endog, "name", None) or (columns[0] if columns else "of the model")
            raise ValueError(
                "the decision rule reads a standardised coefficient, which z-scores the outcome"
                + " as well as the predictors, but the outcome " + repr(str(label))
                + " has standard deviation " + format(sd, ".3g") + " in the " + name
                + ": z-score it, (y - y.mean()) / y.std(), on the rows the model uses"
            )
"""
RESULT_CHECKS_SOURCE = (
    _SOURCE.replace("__LINEAR_MODELS__", repr(LINEAR_MODELS))
    .replace("__UNIT_SD__", repr(UNIT_SD))
    .replace("__MODEL_ROWS_NOTE__", repr(MODEL_ROWS_NOTE))
)
