"""Result checks that need the model that reports the estimate, run inside every model step.

A marp_norms WLS option at c83e4c2 reported n as the rows it was given (10,195) while its formula
dropped the rows with a missing covariate and fitted 10,170: n is the rows the model used. The
same option left the outcome in its raw units under a decision rule that reads a standardised
coefficient, which the template path z-scores; with the rescaled product term it reported 0.0747
where the consistent estimate was 0.034.
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
