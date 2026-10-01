from __future__ import annotations

MAIN_TEMPLATE = """

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

    def _validate(payload):
        if not isinstance(payload, dict):
            raise ValueError("estimate() must return a dict")
        keys = ("estimate", "ci_low", "ci_high", "p_value", "n")
        out = {key: _finite(payload, key) for key in keys}
        if not 0.0 <= out["p_value"] <= 1.0:
            raise ValueError("p_value must be between 0 and 1")
        if out["ci_low"] > out["ci_high"]:
            raise ValueError("ci_low must not exceed ci_high")
        out["n"] = int(out["n"])
        extra = payload.get("extra", {})
        if not isinstance(extra, dict):
            raise ValueError("extra must be a dict of floats")
        out["extra"] = {str(k): _finite(extra, k) for k in extra}
        return out

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
        trace = {
            "step_id": step_id,
            "option_id": option_id,
            "rows_before": rows_before,
            "rows_after": rows_before,
            "note": "",
        }
        if kind == "model":
            result = _validate(estimate(df, ctx))
            _emit("BORGES_TRACE ", trace)
            _emit("BORGES_RESULT ", result)
            return
        out = apply(df, ctx)
        if not isinstance(out, _pd.DataFrame):
            raise TypeError("apply() must return a DataFrame, got " + type(out).__name__)
        _os.makedirs("state", exist_ok=True)
        out.to_parquet(state_df)
        with open(state_ctx, "w") as handle:
            _json.dump(ctx, handle)
        trace["rows_after"] = int(len(out))
        _emit("BORGES_TRACE ", trace)
    except BaseException as exc:
        lines = [line for line in _tb.format_exc().strip().splitlines() if line.strip()]
        roots = {_os.getcwd(), _os.path.realpath(_os.getcwd())}

        def _clean(text):
            for root in sorted(roots, key=len, reverse=True):
                text = text.replace(root + _os.sep, "").replace(root, "")
            return text

        _emit(
            "BORGES_ERROR ",
            {
                "type": type(exc).__name__,
                "message": _clean(str(exc)),
                "where": _clean("\\n".join(lines[-6:])),
            },
        )
        _sys.exit(1)


__borges_main()
"""
