from __future__ import annotations

SPLIT_HALF_SOURCE = """
    def _check_split_half(df, ctx, result):
        k_splits = 4
        max_ratio = 6.0
        min_ratio = 0.025
        min_rows = 40
        rows = int(len(df))
        se = (result["ci_high"] - result["ci_low"]) / 3.92
        if rows < min_rows or not se > 0:
            return
        rng = _np.random.RandomState(20240607)
        gaps = []
        for _ in range(k_splits):
            order = rng.permutation(rows)
            halves = (order[: rows // 2], order[rows // 2 :])
            values = []
            for part in halves:
                try:
                    half_ctx = _json.loads(_json.dumps(ctx))
                    half = estimate(df.iloc[part].reset_index(drop=True), half_ctx)
                    value = float(half["estimate"])
                except BaseException:
                    return
                if not _math.isfinite(value):
                    return
                values.append(value)
            gaps.append(abs(values[0] - values[1]))
        median_gap = float(_np.median(gaps))
        ratio = median_gap / (2.0 * se)
        if 0.0 < ratio < min_ratio:
            raise ValueError(
                "the reported interval implies a standard error of " + _num(se)
                + ", but estimates on random halves of the data differ by a median of only "
                + _num(median_gap) + ", about " + _num(1.0 / ratio)
                + " times less than that standard error implies: the interval is far too wide"
                + " (check that the estimate and the interval are on the same scale and units;"
                + " prefer statsmodels inference)"
            )
        if ratio > max_ratio:
            raise ValueError(
                "the reported interval implies a standard error of " + _num(se)
                + ", but estimates on random halves of the data differ by a median of "
                + _num(median_gap) + ", about " + _num(ratio)
                + " times more than that standard error allows: the interval is far too narrow"
                + " (check the standard error formula; prefer statsmodels inference)"
            )
"""
