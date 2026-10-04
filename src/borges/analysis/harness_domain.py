"""Values a data step turns into NaN or infinity.

np.log1p of a balance below -1, a log or square root of zero or a negative number, or a division
by zero leaves NaN or infinity in the new column, and every model downstream then fails or loses
those rows. numpy warns when that happens; a step that gains non-finite values while numpy warned
is refused with the cause, so the coder repairs the step that made them.
"""

from __future__ import annotations

DOMAIN_SOURCE = """
    import warnings as _warnings

    domain_cues = ("invalid value", "divide by zero")

    def _non_finite(frame):
        counts = {}
        for col in frame.columns:
            series = frame[col]
            if not isinstance(series, _pd.Series) or not _pd.api.types.is_numeric_dtype(series):
                continue
            if _pd.api.types.is_bool_dtype(series):
                continue
            values = series.to_numpy(dtype=float, na_value=_np.nan)
            counts[col] = int((~_np.isfinite(values)).sum())
        return counts

    def _apply_watching_domain(df, ctx):
        counts = _non_finite(df)
        with _warnings.catch_warnings(record=True) as caught:
            _warnings.simplefilter("always", RuntimeWarning)
            out = apply(df, ctx)
        messages = [
            str(w.message)
            for w in caught
            if issubclass(w.category, RuntimeWarning)
            and any(cue in str(w.message) for cue in domain_cues)
        ]
        return out, counts, messages

    def _check_domain(out, counts, messages):
        if not messages or not isinstance(out, _pd.DataFrame):
            return
        for col, now in _non_finite(out).items():
            gained = now - counts.get(col, 0)
            if gained > 0:
                raise ValueError(
                    "the step turned " + str(gained) + " of " + str(len(out)) + " values of '"
                    + str(col) + "' into NaN or infinity (numpy: " + messages[0] + "): a log or "
                    "square root of zero or negative values, or a division by zero. Use a "
                    "transform defined for every value the column takes: np.log1p needs values "
                    "above -1, while np.arcsinh and np.sign(x) * np.log1p(np.abs(x)) accept any"
                )
"""
