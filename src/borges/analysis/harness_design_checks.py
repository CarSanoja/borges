"""Model checks that need the reported term's column, run inside every model step.

A marp_norms clustered-SE option at 508fe2e fitted wb ~ relig_z*cnorm_z built as one column, with
neither relig_z nor cnorm_z in the model: the interaction's coefficient then carries both main
effects, and the option moved the estimate while claiming to change only the standard errors.
The parents were float32, so the product is matched to float32 precision.

A marp_norms WLS option at c83e4c2 z-scored the product religiosity x cnorms after multiplying,
next to z-scored main effects: the term is then the product divided by its own standard deviation,
which depends on where the two scales put their zeros, and the estimate came out 2.9 times the
interaction's coefficient on the scale of its main effects. A product term must be the raw product,
the product of the z-scores, or the product of the main-effect columns as they enter the model.
"""

from __future__ import annotations

PRODUCT_MAX_COLUMNS = 150

DESIGN_CHECKS_SOURCE = """
    def _check_offset(design):
        if __DESIGN_CHECK__ and __OFFSET__ and design.get("offset") is False:
            raise ValueError(
                "the option's spec fits an offset (for example offset=np.log(games)),"
                + " but the " + str(design["model"]) + " that reports the estimate has"
                + " none, so it models counts per row instead of a rate: pass"
                + " offset=np.log(df[...]) (or exposure=) to the model"
            )

    def _product_columns(term, rows):
        numeric = [
            c for c in rows.columns
            if _pd.api.types.is_numeric_dtype(rows[c]) and rows[c].nunique() > 2
        ][:__PRODUCT_MAX_COLUMNS__]
        values = {c: rows[c].to_numpy(dtype=float) for c in numeric}
        if any(_np.allclose(values[c], term, rtol=1e-5, atol=1e-9) for c in numeric):
            return None
        for i, a in enumerate(numeric):
            for b in numeric[i + 1:]:
                if _np.allclose(values[a] * values[b], term, rtol=1e-5, atol=1e-9):
                    return a, b
        centred = term - term.mean()
        spread = float(_np.linalg.norm(centred))
        if spread == 0:
            return None
        for i, a in enumerate(numeric):
            for b in numeric[i + 1:]:
                product = values[a] * values[b]
                product = product - product.mean()
                size = float(_np.linalg.norm(product))
                if size and abs(float(product @ centred)) / (size * spread) > 1 - 1e-9:
                    return a, b
        return None

    def _slope(target, column):
        column = column - column.mean()
        return float(column @ (target - target.mean())) / float(column @ column)

    def _model_column(x, found, column):
        for j in range(x.shape[1]):
            if j == found or _np.std(x[:, j]) == 0:
                continue
            if abs(_np.corrcoef(x[:, j], column)[0, 1]) > 1 - 1e-6:
                return j
        return None

    def _in_model(x, found, column):
        return _model_column(x, found, column) is not None

    def _check_product_scale(x, found, rows, pair):
        a, b = (rows[c].to_numpy(dtype=float) for c in pair)
        scale = _slope(x[:, found], a * b)
        own = [_slope(x[:, _model_column(x, found, v)], v) for v in (a, b)]
        accepted = (1.0, 1.0 / (_np.std(a, ddof=1) * _np.std(b, ddof=1)), own[0] * own[1])
        if any(abs(scale / s - 1) < 0.05 for s in accepted if s):
            return
        raise ValueError(
            "the reported coefficient is on a rescaled product of " + pair[0] + " and "
            + pair[1] + ": the term is " + format(scale * own[0] ** -1 * own[1] ** -1, ".3g")
            + " times the product of the model's own " + pair[0] + " and " + pair[1]
            + " terms, so its coefficient is not the interaction on the scale of its main"
            + " effects (z-scoring a product after multiplying rescales it by its own spread);"
            + " build the term as the product of the two main-effect columns as they enter the"
            + " model, for example the product of the z-scores"
        )

    def _check_main_effects(frame, estimate):
        if not __DESIGN_CHECK__ or not isinstance(estimate, (int, float)):
            return
        for _, exog, names, model_id in reversed(_designs):
            if model_id in _helpers:
                continue
            found = _exposure_index(_fits.get(model_id), estimate, len(names))
            if found is None:
                continue
            endog, _ = _model_endog(_endogs.get(model_id))
            try:
                x = _np.asarray(exog, dtype=float)
                rows = frame.loc[endog.index]
            except Exception:
                return
            if x.ndim != 2 or x.shape[0] != len(rows) or not _np.isfinite(x).all():
                return
            step = max(1, int(_math.ceil(len(rows) / __OUTCOME_MAX_ROWS__)))
            x, rows = x[::step], rows.iloc[::step]
            pair = _product_columns(x[:, found], rows)
            if pair is None:
                return
            missing = [c for c in pair if not _in_model(x, found, rows[c].to_numpy(dtype=float))]
            if missing:
                raise ValueError(
                    "the reported coefficient is the interaction " + pair[0] + " x " + pair[1]
                    + ", but the model leaves out " + ", ".join(map(str, missing))
                    + ": without its main effects the interaction's coefficient absorbs them;"
                    + " add " + pair[0] + " and " + pair[1] + " to the model as their own terms"
                )
            _check_product_scale(x, found, rows, pair)
            return
"""
