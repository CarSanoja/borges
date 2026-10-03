from __future__ import annotations

NORMALISE_SOURCE = """
    _INTERCEPTS = ("const", "Intercept", "intercept")

    def _scalar(value):
        if hasattr(value, "item") and getattr(value, "size", 0) == 1:
            return value.item()
        if isinstance(value, (list, tuple)) and len(value) == 1:
            return _scalar(value[0])
        return value

    def _from_results(res):
        params = res.params
        names = [n for n in getattr(params, "index", []) if n not in _INTERCEPTS]
        if len(names) != 1:
            raise ValueError(
                "estimate() returned a fitted model with " + str(len(names))
                + " non-intercept terms (" + ", ".join(map(str, names[:6])) + "); return a dict "
                + "with estimate, ci_low, ci_high, p_value and n for the one term the question "
                + "is about, for example fit.params[term] and fit.conf_int().loc[term]"
            )
        term = names[0]
        ci = res.conf_int().loc[term]
        return {
            "estimate": params[term],
            "ci_low": ci.iloc[0],
            "ci_high": ci.iloc[1],
            "p_value": res.pvalues[term],
            "n": res.nobs,
        }

    def _from_sequence(seq):
        keys = __RESULT_KEYS__
        if len(seq) == len(keys):
            return dict(zip(keys, seq))
        if len(seq) == 4 and isinstance(seq[1], (list, tuple)) and len(seq[1]) == 2:
            return {
                "estimate": seq[0], "ci_low": seq[1][0], "ci_high": seq[1][1],
                "p_value": seq[2], "n": seq[3],
            }
        raise ValueError(
            "estimate() returned a sequence of " + str(len(seq)) + " items; return a dict or a "
            + "tuple (estimate, ci_low, ci_high, p_value, n)"
        )

    def _normalise_result(payload):
        keys = __RESULT_KEYS__
        fitted = ("params", "conf_int", "pvalues")
        if all(hasattr(payload, name) for name in fitted):
            payload = _from_results(payload)
        elif isinstance(payload, (tuple, list)):
            payload = _from_sequence(payload)
        if isinstance(payload, dict):
            return {k: (_scalar(v) if k in keys else v) for k, v in payload.items()}
        if isinstance(payload, (bool, _np.bool_)) or isinstance(payload, _numbers.Real):
            raise ValueError(
                "estimate() returned a bare number; it must return a dict with estimate, "
                + "ci_low, ci_high, p_value and n (a 95% interval and a p-value are required)"
            )
        raise ValueError(
            "estimate() must return a dict with estimate, ci_low, ci_high, p_value and n, "
            + "not a " + type(payload).__name__
        )
"""
