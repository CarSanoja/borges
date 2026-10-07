"""A reported estimate that rests on a group of a handful of rows, checked in full universes only.

A live fertility_religiosity run on 7 Oct 2026 found its smallest flip by excluding the women
unsure of either period date: the interaction became 4.88 [2.67, 7.10], p 1.6e-5, n 143, and two
single women at high fertility, both with religiosity near 1.2, made the whole effect. With so few
rows one or two answers decide the coefficient and its standard error. The check counts the rows
of each group the reported term compares (the four cells of an interaction of two 0/1 columns, or
the two levels of a 0/1 exposure). The smoke run samples rows, so it never applies there.
"""

from __future__ import annotations

MIN_CELL_ROWS = 5

CELL_CHECK_SOURCE = """
    def _is_binary(column):
        values = _np.unique(column)
        return values.size == 2 and bool(values[0] == 0.0 and values[1] == 1.0)

    def _cell_counts(x, found):
        term = x[:, found]
        if not _is_binary(term):
            return None
        on = term == 1
        parents = [
            j for j in range(x.shape[1])
            if j != found and bool((x[on, j] == 1).all()) and _is_binary(x[:, j])
        ]
        for i, a in enumerate(parents):
            for b in parents[i + 1:]:
                if _np.array_equal(x[:, a] * x[:, b], term):
                    codes = 2 * x[:, a].astype(int) + x[:, b].astype(int)
                    return [int(n) for n in _np.bincount(codes, minlength=4)]
        return [int((~on).sum()), int(on.sum())]

    def _check_thin_cells(estimate):
        if not __FULL_DATA_CHECKS__ or not isinstance(estimate, (int, float)):
            return
        for _, exog, names, model_id in reversed(_designs):
            if model_id in _helpers:
                continue
            found = _exposure_index(_fits.get(model_id), estimate, len(names))
            if found is None:
                continue
            try:
                x = _np.asarray(exog, dtype=float)
            except Exception:
                return
            if x.ndim != 2 or not _np.isfinite(x).all():
                return
            counts = _cell_counts(x, found)
            if counts is not None and min(counts) < __MIN_CELL_ROWS__:
                raise ValueError(
                    "the reported estimate rests on a group of only " + str(min(counts))
                    + " rows (group sizes " + str(counts) + "): with so few rows one or two"
                    + " answers decide the coefficient and its standard error, so this"
                    + " universe is left out of the analysis instead of counting as a result"
                )
            return
"""
