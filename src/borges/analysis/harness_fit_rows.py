"""Name the rows the model fitted by the row key, when that can be checked.

The probe records the labels of the rows statsmodels kept and a position-weighted sum of the
outcome it fitted. The labels are positions in the frame the harness passed to the step only if
the step did not rebuild or reorder it, so the keys are reported only when the outcome at those
positions gives the same weighted sum; otherwise nothing is reported, never a wrong list.
"""

from __future__ import annotations

FIT_ROWS_SOURCE = """
    def _fit_keys(design, df):
        rows = design.pop("rows", None)
        fitted = design.pop("endog_check", None)
        key, outcome = __ROW_KEY__, design.get("outcome")
        if rows is None or fitted is None or key is None or key not in df.columns:
            return
        if outcome not in df.columns or not all(0 <= r < len(df) for r in rows):
            return
        try:
            values = _pd.to_numeric(df[outcome].iloc[rows], errors="coerce").to_numpy(float)
            seen = float(values @ _np.arange(1, len(values) + 1, dtype=float))
        except Exception:
            return
        if not _math.isfinite(seen) or abs(seen - fitted) > 1e-9 * max(1.0, abs(seen)):
            return
        design["row_keys"] = [str(v) for v in df[key].iloc[rows]]
"""
