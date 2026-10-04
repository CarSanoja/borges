from __future__ import annotations

from borges.analysis.models import StepTrace


class EffectTrace(StepTrace):
    effects: dict[str, object] | None = None


CHECKS_SOURCE = """
    def _check_columns(before_cols, rows_before, out, kind):
        lost = [c for c in before_cols if c not in out.columns]
        if not lost or (kind != "filter" and len(out) != rows_before):
            return
        raise ValueError(
            "apply() dropped the columns " + repr(lost)
            + ": filters and steps that keep the rows never drop columns, because later"
            + " steps and other options may need them; only a step that aggregates rows"
            + " (one row per group) may return fewer columns; to choose which covariates a"
            + " later model uses, keep every column and store the list of names in ctx (for"
            + " example ctx['covariates'] = [...]); the model step reads that list"
        )

    def _carry_group_attributes(before, out):
        lost = [c for c in before.columns if c not in out.columns]
        if not lost or len(out) >= len(before):
            return out
        keys = [
            c for c in out.columns
            if c in before.columns and out[c].notna().all() and out[c].is_unique
        ]
        if len(keys) != 1:
            return out
        key = keys[0]
        groups = before.groupby(key, dropna=True)
        constant = [c for c in lost if bool((groups[c].nunique(dropna=False) <= 1).all())]
        if not constant:
            return out
        first = groups[constant].first().reset_index()
        merged = out.merge(first, on=key, how="left", validate="one_to_one")
        merged.index = out.index
        return merged

    def _check_produces(out, ctx):
        import fnmatch as _fnmatch

        present = list(map(str, out.columns)) + list(map(str, ctx))
        for name in __PRODUCES__:
            if any(char in name for char in "*?["):
                found = bool(_fnmatch.filter(present, name))
            else:
                found = name in out.columns or name in ctx
            if not found:
                raise ValueError(
                    "this step must produce " + repr(name)
                    + " (every option of the step writes the same names so later steps can read"
                    + " them); it is missing. An option that changes nothing still writes it, as an"
                    + " unchanged copy of the column it is built from, or as 0 for an indicator"
                    + " that none of its rows has. Columns now: "
                    + repr(list(map(str, out.columns))[:80])
                    + "; ctx keys: " + repr(list(map(str, ctx)))
                )

    def _explain(exc, seen):
        text = str(exc)
        lowered = text.lower()
        if (
            isinstance(exc, AttributeError)
            and "statsmodels" in lowered
            and any("has no attribute '" + n + "'" in lowered for n in ("norm", "t", "chi2", "f"))
        ):
            text = (
                text + " | statsmodels has no probability distributions here: read p-values"
                + " from the fitted result (result.pvalues) and intervals from"
                + " result.conf_int(); if you really need a distribution use scipy.stats.norm"
            )
        if seen and seen.get("missing") and (
            "nan" in lowered or "same length" in lowered or "missing" in lowered
        ):
            text = (
                text + " | missing values per column (" + str(seen.get("rows", 0)) + " rows): "
                + repr(seen["missing"])
                + "; keep complete cases of the columns the step uses before fitting"
            )
        if not seen or not (isinstance(exc, KeyError) or "are in the [columns]" in text):
            return text
        cols = seen["columns"]
        tail = " ..." if len(cols) > 80 else ""
        key = exc.args[0] if isinstance(exc, KeyError) and exc.args else None
        hint = ""
        if isinstance(key, str) and key in cols and key not in seen["ctx"]:
            hint = (
                "; " + repr(key) + " is a column of df, not a ctx key: read df[" + repr(key)
                + "] and never look a column name up in ctx"
            )
        return (
            text + " | columns available (" + str(len(cols)) + "): " + repr(cols[:80]) + tail
            + "; ctx keys: " + repr(seen["ctx"]) + hint
        )
"""

EFFECTS_SOURCE = """
    def _f(value):
        try:
            value = float(value)
        except (TypeError, ValueError):
            return None
        return value if _math.isfinite(value) else None

    def _aligned(before, out):
        if before.index.is_unique and out.index.is_unique:
            if len(out.index.difference(before.index)) == 0:
                reset = len(out) < len(before) and out.index.equals(_pd.RangeIndex(len(out)))
                if not reset:
                    return before.loc[out.index], out
        if len(before) == len(out):
            return before.reset_index(drop=True), out.reset_index(drop=True)
        return None

    def _changed_columns(before, out):
        pair = _aligned(before, out)
        if pair is None:
            return []
        old, new = pair
        changed = []
        for col in before.columns:
            if col not in out.columns:
                continue
            try:
                a, b = old[col], new[col]
                same = (a.to_numpy(dtype=object) == b.to_numpy(dtype=object)) | (
                    a.isna().to_numpy() & b.isna().to_numpy()
                )
                if not bool(_np.all(same)):
                    changed.append(str(col))
            except Exception:
                continue
        return changed

    def _dropped_by(before, out):
        found = {}
        for col in before.columns:
            if len(found) >= 5:
                break
            try:
                if col not in out.columns or before[col].nunique(dropna=False) > 10:
                    continue
                gone = before[col].value_counts(dropna=False).sub(
                    out[col].value_counts(dropna=False), fill_value=0
                )
                gone = {str(k): int(v) for k, v in gone.items() if v > 0}
            except Exception:
                continue
            if gone:
                found[str(col)] = gone
        return found

    def _column_stats(out, names):
        stats = {}
        for col in names:
            series = out[col]
            if not _pd.api.types.is_numeric_dtype(series.dtype):
                continue
            if len(stats) >= 10:
                break
            values = series.astype(float)
            try:
                head = values.sort_index().iloc[:200]
            except TypeError:
                head = values.iloc[:200]
            stats[str(col)] = {
                "mean": _f(values.mean()),
                "sd": _f(values.std()),
                "min": _f(values.min()),
                "max": _f(values.max()),
                "n_missing": int(values.isna().sum()),
                "probe": {str(i): _f(v) for i, v in head.items()},
            }
        return stats

    def _effects(before, out, ctx_before, ctx):
        added = [c for c in out.columns if c not in before.columns]
        changed = _changed_columns(before, out)
        effects = {
            "rows_before": int(len(before)),
            "rows_after": int(len(out)),
            "added": [str(c) for c in added],
            "changed": changed,
            "columns": _column_stats(out, [*added, *changed]),
            "ctx_added": {
                str(k): repr(ctx[k])[:200] for k in ctx if k not in ctx_before
            },
        }
        if len(out) < len(before):
            dropped = _dropped_by(before, out)
            if dropped:
                effects["dropped_rows_by"] = dropped
        return effects
"""
