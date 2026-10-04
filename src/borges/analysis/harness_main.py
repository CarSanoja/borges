from __future__ import annotations

from borges.analysis.harness_design import (
    DESIGN_CONDITION_LIMIT,
    DESIGN_MAX_ROWS,
    DESIGN_SOURCE,
    DESIGN_WIDE_COLUMNS,
)
from borges.analysis.harness_design_errors import DESIGN_ERRORS_SOURCE
from borges.analysis.harness_effects import CHECKS_SOURCE, EFFECTS_SOURCE
from borges.analysis.harness_fingerprint import FINGERPRINT_SOURCE
from borges.analysis.harness_hints import HINTS_SOURCE
from borges.analysis.harness_normalise import NORMALISE_SOURCE
from borges.analysis.harness_outcome import LOG_LINK_MODELS, OUTCOME_MAX_ROWS, OUTCOME_SOURCE
from borges.analysis.harness_split_half import SPLIT_HALF_SOURCE
from borges.analysis.model_spec.render_design import ALIAS_NOTE

_TEMPLATE = """

def __borges_main():
    import json as _json
    import math as _math
    import numbers as _numbers
    import numpy as _np
    import os as _os
    import random as _random
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
        if high - low <= max(1e-6 * abs(est), 1e-9):
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

__NORMALISE__

    def _validate(payload):
        payload = _normalise_result(payload)
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
__HINTS__
__DESIGN__
__FINGERPRINT__
    seen = {}
    _np.random.seed(0)
    _random.seed(0)
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
        nulls = df.isna().sum()
        seen["rows"] = int(len(df))
        seen["missing"] = {str(k): int(v) for k, v in nulls[nulls > 0].items()}
        seen["nonnumeric"] = [
            str(c) for c in df.columns
            if not _pd.api.types.is_numeric_dtype(df[c]) and not _pd.api.types.is_bool_dtype(df[c])
        ][:200]
        seen["ctx_lists"] = [
            str(item) for value in ctx.values() if isinstance(value, list) for item in value
        ]
        seen["frame"] = df
        trace = {
            "step_id": step_id,
            "option_id": option_id,
            "rows_before": rows_before,
            "rows_after": rows_before,
            "note": "",
        }
        if kind == "model":
            _install_design_probe()
            raw_result = estimate(df, ctx)
            if isinstance(raw_result, dict) and isinstance(raw_result.get("note"), str):
                trace["note"] = raw_result["note"][:500]
            reported = raw_result.get("estimate") if isinstance(raw_result, dict) else None
            design = _design_payload(
                list(map(str, df.columns)), seen.get("ctx_lists", []), reported
            )
            if design is not None:
                trace["design"] = design
                scale = _outcome_scale(df, reported)
                if scale is not None:
                    design["outcome_log"] = scale
                if __DESIGN_CHECK__ and design["deficient"]:
                    raise ValueError(_design_error(design))
                if __DESIGN_CHECK__ and design["no_intercept"]:
                    raise ValueError(_intercept_error(design))
                if design["aliased"]:
                    alias = __ALIAS_NOTE__ + ", ".join(design["aliased"])
                    trace["note"] = (alias + "; " + trace["note"] if trace["note"] else alias)[:500]
            result = _validate(raw_result)
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
        out = _carry_group_attributes(df, out)
        _check_columns(seen["columns"], rows_before, out, kind)
        _check_produces(out, ctx)
        _check_ctx(ctx)
        _os.makedirs("state", exist_ok=True)
        out.to_parquet(state_df)
        with open(state_ctx, "w") as handle:
            _json.dump(ctx, handle)
        trace["rows_after"] = int(len(out))
        trace["fingerprint"] = _fingerprint(out, ctx)
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
                "message": _clean(_explain(exc, seen) + _encoding_hint(exc, seen, kind)),
                "where": _clean("\\n".join(lines[-6:])),
            },
        )
        _sys.exit(1)


__borges_main()
"""
MAIN_TEMPLATE = (
    _TEMPLATE.replace("__NORMALISE__", NORMALISE_SOURCE.strip("\n"))
    .replace("__SPLIT_HALF_CHECK__", SPLIT_HALF_SOURCE.strip("\n"))
    .replace("__CHECKS__", CHECKS_SOURCE.strip("\n"))
    .replace("__EFFECTS__", EFFECTS_SOURCE.strip("\n"))
    .replace("__HINTS__", HINTS_SOURCE.strip("\n"))
    .replace(
        "__DESIGN__",
        "\n\n".join(x.strip("\n") for x in (DESIGN_SOURCE, DESIGN_ERRORS_SOURCE, OUTCOME_SOURCE)),
    )
    .replace("__OUTCOME_MAX_ROWS__", repr(OUTCOME_MAX_ROWS))
    .replace("__LOG_LINK_MODELS__", repr(LOG_LINK_MODELS))
    .replace("__FINGERPRINT__", FINGERPRINT_SOURCE.strip("\n"))
    .replace("__DESIGN_CONDITION_LIMIT__", repr(DESIGN_CONDITION_LIMIT))
    .replace("__DESIGN_MAX_ROWS__", repr(DESIGN_MAX_ROWS))
    .replace("__ALIAS_NOTE__", repr(ALIAS_NOTE))
    .replace("__DESIGN_WIDE_COLUMNS__", repr(DESIGN_WIDE_COLUMNS))
)
