from __future__ import annotations

HINTS_SOURCE = """
    def _encoding_hint(exc, seen, kind):
        text = str(exc)
        if kind != "model" or not seen or "could not convert string to float" not in text:
            return ""
        frame = seen.get("frame")
        names = list(seen.get("nonnumeric", []))
        value = None
        if "'" in text:
            value = text.split("'", 1)[1].rsplit("'", 1)[0]
        holders = []
        if frame is not None and value is not None:
            for name in names:
                try:
                    if (frame[name].astype(str) == value).any():
                        holders.append(name)
                except Exception:
                    continue
        listed = [n for n in names if n in set(seen.get("ctx_lists", []))]
        found = holders or listed or names
        if not found:
            return ""
        return (
            " | non-numeric columns among the model inputs: " + repr(found[:30])
            + "; encode them with pd.get_dummies(..., drop_first=True, dtype=float) before"
            + " fitting, including every categorical covariate that comes from a ctx list"
        )

    def _fit_key_hint(exc):
        if not isinstance(exc, KeyError) or not exc.args or not isinstance(exc.args[0], str):
            return ""
        key = exc.args[0]
        tb, frames = exc.__traceback__, []
        while tb is not None:
            frames.append((tb.tb_frame, tb.tb_lineno))
            tb = tb.tb_next
        import linecache as _linecache

        for frame, lineno in reversed(frames):
            fitted = [
                (name, value)
                for name, value in list(frame.f_locals.items())
                if hasattr(value, "bse") and hasattr(getattr(value, "params", None), "index")
            ]
            if not fitted:
                continue
            line = _linecache.getline(frame.f_code.co_filename, lineno)
            named = [(n, v) for n, v in fitted if n + "." in line]
            name, value = (named or fitted)[-1]
            terms = [str(t) for t in value.params.index]
            if key in terms:
                return ""
            return (
                " | " + repr(key) + " is not a column lookup that failed but a term missing from"
                + " the fitted model " + name + ", whose terms are " + repr(terms[:20]) + ": the"
                + " formula or design that was fitted does not include " + repr(key) + ". Check"
                + " every branch that builds the formula (with and without covariates); the"
                + " exposure must be in all of them"
            )
        return ""

    def _singular_hint(exc, seen, kind):
        text = str(exc).lower()
        if kind != "model" or not seen or not ("singular matrix" in text or "finite" in text):
            return ""
        frame = seen.get("frame")
        if frame is None:
            return ""
        large = []
        for name in dict.fromkeys(seen.get("ctx_lists", [])):
            if name in frame.columns and _pd.api.types.is_numeric_dtype(frame[name]):
                top = float(frame[name].abs().max())
                if top >= 1000:
                    large.append(name + " up to " + format(top, ".3g"))
        if not large:
            return ""
        return (
            " | covariates with large values (" + ", ".join(large[:10]) + ") leave the"
            + " maximum-likelihood solver with a singular Hessian or no finite interval:"
            + " rescale each numeric covariate that is not the exposure,"
            + " (x - x.mean()) / x.std(), before fitting; the"
            + " exposure's coefficient does not change"
        )

    def _spelled_hint(exc, seen):
        if not isinstance(exc, KeyError) or not seen:
            return ""
        import re as _re

        listed = _re.search(r"\[((?:'[^']*'(?:,\s*)?)+)\]", str(exc))
        letters = _re.findall(r"'([^']*)'", listed.group(1)) if listed else []
        if len(letters) < 3 or any(len(letter) != 1 for letter in letters):
            return ""
        names = list(seen.get("columns", [])) + list(seen.get("ctx", []))
        found = [n for n in dict.fromkeys(map(str, names)) if set(n) == set(letters)]
        if not found:
            return ""
        return (
            " | the missing keys are the letters of " + repr(found[0]) + ": a single name was"
            + " used where a list of names is expected, so pandas read it letter by letter;"
            + " wrap it in a list, df[[" + repr(found[0]) + "]], or when it comes from ctx,"
            + " [ctx[" + repr(found[0]) + "]] if isinstance(ctx[" + repr(found[0]) + "], str)"
        )
"""
