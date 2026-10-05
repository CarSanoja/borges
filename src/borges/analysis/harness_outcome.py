"""Outcome-scale check run inside every model step.

It tells whether the reported estimate is on a log scale of the outcome: the model's outcome is
log() or log1p() of a column of the data, or a log-link count model reports its raw coefficient.
The report then says so, instead of reading the estimate as additional units of the outcome.
The outcome is named by the first column of the data it equals: a marp_religiosity flip at 508fe2e
copied physical well-being into the column 'wellbeing' that the baseline filled with overall
well-being, and was reported as a re-analysis of the same outcome.
A marp_norms Gamma GLM at 0b92e6c passed `sm.families.links.log()`, the lower-case class statsmodels
keeps as a deprecated alias, and its log-scale coefficient was read under a standardised rule with
no note; the link is matched whatever its case (2 of 207 recorded model codes use that class).
"""

from __future__ import annotations

OUTCOME_MAX_ROWS = 5000
LOG_LINK_MODELS = ("Poisson", "NegativeBinomial", "NegativeBinomialP", "GeneralizedPoisson")

OUTCOME_SOURCE = """
    _endogs = {}

    def _record_endog(model):
        _endogs[id(model)] = model

    def _model_endog(model):
        try:
            family = getattr(model, "family", None)
            link = type(getattr(family, "link", None)).__name__ if family is not None else ""
            return getattr(getattr(model, "data", None), "orig_endog", None), link
        except Exception:
            return None, ""

    def _endog_levels(model_id):
        try:
            endog, _ = _model_endog(_endogs.get(model_id))
            values = _np.asarray(endog, dtype=float).ravel()
            return int(_np.unique(values[_np.isfinite(values)]).size)
        except Exception:
            return None

    def _logged_column(endog, frame):
        try:
            values = _pd.Series(_np.asarray(endog, dtype=float).ravel(), index=endog.index)
            rows = frame.loc[values.index]
        except Exception:
            return None
        step = max(1, int(_math.ceil(len(values) / __OUTCOME_MAX_ROWS__)))
        values, rows = values.iloc[::step], rows.iloc[::step]
        for column in rows.columns:
            if not _pd.api.types.is_numeric_dtype(rows[column]) or rows[column].nunique() < 3:
                continue
            raw = rows[column].to_numpy(dtype=float)
            if not _np.isfinite(raw).all() or raw.min() < 0:
                continue
            with _np.errstate(divide="ignore"):
                for kind, made in (("log1p", _np.log1p(raw)), ("log", _np.log(raw))):
                    close = _np.allclose(values, made, rtol=1e-9, atol=1e-9)
                    if _np.isfinite(made).all() and close:
                        return kind, str(column)
        return None

    def _reporting_models(estimate):
        if not isinstance(estimate, (int, float)):
            return
        for name, _, _, model_id in reversed(_designs):
            if model_id in _helpers:
                continue
            params = _fits.get(model_id)
            if params is not None and any(
                abs(p - estimate) <= 1e-6 * max(1.0, abs(estimate)) for p in params
            ):
                yield name, model_id

    def _first_equal_column(endog, frame):
        try:
            values = _pd.Series(_np.asarray(endog, dtype=float).ravel(), index=endog.index)
            rows = frame.loc[values.index]
        except Exception:
            return None
        step = max(1, int(_math.ceil(len(values) / __OUTCOME_MAX_ROWS__)))
        values, rows = values.iloc[::step], rows.iloc[::step]
        if values.nunique() < 3:
            return None
        for column in rows.columns:
            if not _pd.api.types.is_numeric_dtype(rows[column]):
                continue
            raw = rows[column].to_numpy(dtype=float)
            if _np.allclose(values.to_numpy(), raw, rtol=1e-12, atol=0.0, equal_nan=True):
                return str(column)
        return None

    def _outcome_name(frame, estimate):
        for _, model_id in _reporting_models(estimate):
            endog, _ = _model_endog(_endogs.get(model_id))
            name = getattr(endog, "name", None)
            copied = _first_equal_column(endog, frame) if endog is not None else None
            if copied is not None or name is None or name not in frame.columns:
                return copied
            return str(name)
        return None

    def _outcome_scale(frame, estimate):
        for name, model_id in _reporting_models(estimate):
            endog, link = _model_endog(_endogs.get(model_id))
            logged = _logged_column(endog, frame) if endog is not None else None
            if logged is not None:
                return {"kind": logged[0], "column": logged[1]}
            if name in __LOG_LINK_MODELS__ or link.lower() == "log":
                return {"kind": "log link", "column": str(getattr(endog, "name", "") or "outcome")}
        return None
"""
