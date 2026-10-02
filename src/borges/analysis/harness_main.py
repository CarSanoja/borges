from __future__ import annotations

from borges.analysis.harness_effects import CHECKS_SOURCE, EFFECTS_SOURCE
from borges.analysis.harness_split_half import SPLIT_HALF_SOURCE

_TEMPLATE = """

def __borges_main():
    import json as _json
    import math as _math
    import numbers as _numbers
    import numpy as _np
    import os as _os
    import sys as _sys
    import traceback as _tb

    import pandas as _pd

    step_id = __STEP_ID__
    option_id = __OPTION_ID__
    kind = __KIND__

    def _emit(prefix, payload):
        print(prefix + _json.dumps(payload), flush=True)

    def _finite(payload, key):
        if key not in payload:
            raise ValueError("estimate() result is missing key '" + key + "'")
        value = payload[key]
        if isinstance(value, (bool, _np.bool_)) or not isinstance(value, _numbers.Real):
            raise ValueError("estimate() key '" + key + "' must be a number")
        value = float(value)
        if not _math.isfinite(value):
            raise ValueError("estimate() key '" + key + "' must be finite")
        return value

    def _num(value):
        return format(value, ".4g")

    def _check_interval(out):
        low, high, est = out["ci_low"], out["ci_high"], out["estimate"]
        tol = 1e-6 * max(1.0, abs(low), abs(high))
        inside = low - tol <= est <= high + tol
        span = "the 95% interval [" + _num(low) + ", " + _num(high) + "]"
        if low > high:
            raise ValueError(
                span + " is inverted: ci_low must be smaller than ci_high"
                + ("" if inside else " and it does not contain the estimate " + _num(est))
            )
        if low == high:
            raise ValueError(
                span + " is degenerate"
                + ("" if inside else " and does not contain the estimate " + _num(est))
                + ": ci_low must be smaller than ci_high"
            )
        if not inside:
            raise ValueError(
                span + " does not contain the estimate " + _num(est)
            )

    def _check_ctx(ctx):
        bad = []
        for key, value in ctx.items():
            try:
                _json.dumps(value)
            except (TypeError, ValueError):
                bad.append("ctx[" + repr(key) + "] holds a " + type(value).__name__)
        if bad:
            raise TypeError(
                "; ".join(bad)
                + ": ctx may only hold JSON values (numbers, strings, lists and dicts of them);"
                + " return rows in the DataFrame and keep only column names or numbers in ctx"
            )

    def _validate(payload):
        if not isinstance(payload, dict):
            raise ValueError("estimate() must return a dict")
        keys = __RESULT_KEYS__
        out = {key: _finite(payload, key) for key in keys}
        if not 0.0 <= out["p_value"] <= 1.0:
            raise ValueError(
                "p_value " + _num(out["p_value"]) + " is outside the range [0, 1]"
            )
        _check_interval(out)
        if out["n"] < 1 or out["n"] != int(out["n"]):
            raise ValueError(
                "n must be a positive integer (the number of rows used), got " + _num(out["n"])
            )
        out["n"] = int(out["n"])
        extra = payload.get("extra", {})
        if not isinstance(extra, dict):
            raise ValueError("extra must be a dict of floats")
        out["extra"] = {str(k): _finite(extra, k) for k in extra}
        return out

__SPLIT_HALF_CHECK__
__CHECKS__
__EFFECTS__
    seen = {}
    try:
        state_df = _os.path.join("state", "df.parquet")
        state_ctx = _os.path.join("state", "ctx.json")
        df = _pd.read_parquet(state_df if _os.path.exists(state_df) else "data.parquet")
        if _os.path.exists(state_ctx):
            with open(state_ctx) as handle:
                ctx = _json.load(handle)
        else:
            ctx = {}
        rows_before = int(len(df))
        seen.update({"columns": list(map(str, df.columns)), "ctx": list(map(str, ctx))})
        trace = {
            "step_id": step_id,
            "option_id": option_id,
            "rows_before": rows_before,
            "rows_after": rows_before,
            "note": "",
        }
        if kind == "model":
            result = _validate(estimate(df, ctx))
            if __SPLIT_HALF__:
                _check_split_half(df, ctx, result)
            _emit("BORGES_TRACE ", trace)
            _emit("BORGES_RESULT ", result)
            return
        ctx_before = set(ctx)
        before = df.copy() if __SPLIT_HALF__ else None
        out = apply(df, ctx)
        if not isinstance(out, _pd.DataFrame):
            raise TypeError("apply() must return a DataFrame, got " + type(out).__name__)
        _check_columns(seen["columns"], out)
        _check_produces(out, ctx)
        _check_ctx(ctx)
        _os.makedirs("state", exist_ok=True)
        out.to_parquet(state_df)
        with open(state_ctx, "w") as handle:
            _json.dump(ctx, handle)
        trace["rows_after"] = int(len(out))
        if __SPLIT_HALF__:
            try:
                trace["effects"] = _effects(before, out, ctx_before, ctx)
            except Exception:
                pass
        _emit("BORGES_TRACE ", trace)
    except BaseException as exc:
        lines = [line for line in _tb.format_exc().strip().splitlines() if line.strip()]
        roots = {_os.getcwd(), _os.path.realpath(_os.getcwd()), _sys.prefix, _sys.base_prefix}

        def _clean(text):
            for root in sorted(roots, key=len, reverse=True):
                text = text.replace(root + _os.sep, "").replace(root, "")
            return text

        _emit(
            "BORGES_ERROR ",
            {
                "type": type(exc).__name__,
                "message": _clean(_explain(exc, seen)),
                "where": _clean("\\n".join(lines[-6:])),
            },
        )
        _sys.exit(1)


__borges_main()
"""
MAIN_TEMPLATE = (
    _TEMPLATE.replace("__SPLIT_HALF_CHECK__", SPLIT_HALF_SOURCE.strip("\n"))
    .replace("__CHECKS__", CHECKS_SOURCE.strip("\n"))
    .replace("__EFFECTS__", EFFECTS_SOURCE.strip("\n"))
)
