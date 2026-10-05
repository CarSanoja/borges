from __future__ import annotations

VALIDATE_SOURCE = """
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

    def _check_ctx_columns(ctx, out, trace):
        named = ctx.get("covariates")
        if not isinstance(named, list) or not all(isinstance(c, str) for c in named):
            return
        import re as _re

        columns = list(map(str, out.columns))

        def _term_ok(term):
            if term in columns:
                return True
            if not _re.search(r"[():*]", term):
                return False
            return any(name in columns for name in _re.findall(r"[A-Za-z_][A-Za-z0-9_]*", term))

        missing = [c for c in named if not _term_ok(c)]
        if not missing:
            return
        bases = sorted({b for c in missing for b in columns if c.startswith(b + "_")})
        prefixes = tuple(b + "_" for b in bases)
        present = [c for c in columns if c not in bases and c.startswith(prefixes)]
        owner = {c: next((b for b in bases if c.startswith(b + "_")), None) for c in missing}
        def _dummy(column):
            values = set(out[column].dropna().unique().tolist())
            return bool(values) and values <= {0, 1, True, False}

        groups = {b: [c for c in present if c.startswith(b + "_") and _dummy(c)] for b in bases}
        if all(owner.values()) and all(groups[b] for b in set(owner.values())):
            kept = []
            for name in named:
                for column in groups[owner[name]] if name in owner else [name]:
                    if column not in kept:
                        kept.append(column)
            ctx["covariates"] = kept
            note = (
                "ctx['covariates'] named dummies get_dummies did not build (" + ", ".join(missing)
                + "); the ones it built are listed instead (" + ", ".join(kept) + "): the"
                + " reference level does not change the exposure's estimate"
            )
            trace["note"] = (note + "; " + trace["note"] if trace["note"] else note)[:500]
            return
        have = (
            " the returned DataFrame has " + repr(present[:12])
            + " (get_dummies with drop_first=True drops the first level), so list those, or"
            if present
            else ""
        )
        hint = (
            " they look like dummies of " + ", ".join(map(repr, bases)) + ":" + have + " list "
            + ("that column" if len(bases) == 1 else "those columns")
            + " itself and let the model encode it;"
            if bases
            else ""
        )
        raise ValueError(
            "ctx['covariates'] names columns the returned DataFrame does not have: "
            + repr(missing[:12]) + ";" + hint
            + " every covariate must be a column of the DataFrame this step returns"
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

    def _check_kept_rows(out, rows_before):
        if __KEEPS_ROWS__ and len(out) < rows_before:
            raise ValueError(
                "the option says it keeps every row, but its code drops "
                + str(rows_before - len(out)) + " of " + str(rows_before) + " rows: a 'keep all'"
                + " option returns the data unchanged, so remove every filter from it"
            )

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
"""
