"""Design-matrix check run inside every model step.

A statsmodels model whose exog is rank-deficient, has an all-zero column, or whose condition
number (columns scaled to unit length, the threshold statsmodels itself uses to warn about strong
multicollinearity) exceeds DESIGN_CONDITION_LIMIT fails the step with a clear reason. The check
reads the exog of every statsmodels model the step builds; models built with other libraries
are not inspected.
"""

from __future__ import annotations

DESIGN_CONDITION_LIMIT = 1e10
DESIGN_MAX_ROWS = 200000
DESIGN_WIDE_COLUMNS = 500

DESIGN_SOURCE = """
    _designs = []
    _fits = {}

    def _install_design_probe():
        try:
            from statsmodels.base import model as _sm_model
        except Exception:
            return
        original = _sm_model.Model.__init__
        results = _sm_model.LikelihoodModelResults.__init__

        def probed(self, *args, **kwargs):
            original(self, *args, **kwargs)
            try:
                if self.exog is not None:
                    names = list(self.exog_names)
                    _designs.append((type(self).__name__, self.exog, names, id(self)))
            except Exception:
                pass

        def fitted(self, model, params, *args, **kwargs):
            results(self, model, params, *args, **kwargs)
            try:
                _fits[id(model)] = _np.asarray(params, dtype=float).ravel()
            except Exception:
                pass

        _sm_model.Model.__init__ = probed
        _sm_model.LikelihoodModelResults.__init__ = fitted

    def _exposure_index(params, estimate, width):
        if params is None or len(params) != width or not isinstance(estimate, (int, float)):
            return None
        if not _math.isfinite(estimate):
            return None
        with _np.errstate(over="ignore"):
            for values in (params, _np.exp(params), 100.0 * params):
                close = [
                    i for i in range(width)
                    if abs(values[i] - estimate) <= 1e-6 * max(1.0, abs(estimate))
                ]
                if len(close) == 1:
                    return close[0]
        return None

    def _term_of(name, columns):
        best = ""
        for col in columns:
            if len(col) > len(best) and (
                name == col
                or name.startswith(col + "_")
                or name.startswith(col + "[")
                or ("(" + col + ")") in name
                or name.startswith("C(" + col)
            ):
                best = col
        return best or name

    def _alias_split(x, names, scaled, rank, frame_columns, allowed, exposure=None):
        if rank >= x.shape[1]:
            return [], False
        _, sv_all, vt = _np.linalg.svd(scaled, full_matrices=False)
        null = vt[sv_all <= sv_all.max() * max(scaled.shape) * _np.finfo(float).eps]
        involved = [str(names[i]) for i in range(x.shape[1]) if _np.abs(null[:, i]).max() > 1e-6]
        free = all(
            n.lower() in ("const", "intercept") or _term_of(n, frame_columns) in allowed
            for n in involved
        ) or (exposure is not None and str(names[exposure]) not in involved)
        basis = _np.zeros((x.shape[0], 0))
        dropped = []
        for i in range(x.shape[1]):
            residual = scaled[:, i]
            for _ in range(2):
                residual = residual - basis @ (basis.T @ residual)
            size = float(_np.linalg.norm(residual))
            if size >= 1e-7:
                basis = _np.column_stack([basis, residual / size])
            else:
                dropped.append(str(names[i]))
        return dropped, bool(involved) and free and len(dropped) == x.shape[1] - rank

    def _design_payload(frame_columns, allowed=(), estimate=None):
        allowed = set(map(str, allowed))
        models = []
        for model_name, exog, names, model_id in _designs:
            try:
                x = _np.asarray(exog, dtype=float)
            except Exception:
                continue
            if x.ndim != 2 or x.shape[0] == 0 or x.shape[1] == 0 or not _np.isfinite(x).all():
                continue
            if x.shape[0] > __DESIGN_MAX_ROWS__:
                x = x[:: int(_math.ceil(x.shape[0] / __DESIGN_MAX_ROWS__))]
            norms = _np.linalg.norm(x, axis=0)
            dead = [str(names[i]) for i in range(x.shape[1]) if norms[i] == 0]
            scaled = x / _np.where(norms == 0, 1.0, norms)
            sv = _np.linalg.svd(scaled, compute_uv=False)
            tol = sv.max() * max(scaled.shape) * _np.finfo(float).eps
            rank = int((sv > tol).sum())
            cond = float(sv.max() / sv.min()) if sv.min() > 0 else float("inf")
            ones = _np.ones(x.shape[0])
            fitted = x @ _np.linalg.lstsq(x, ones, rcond=None)[0]
            intercept = bool(_np.linalg.norm(fitted - ones) < 1e-6 * _math.sqrt(x.shape[0]))
            exposure = (
                _exposure_index(_fits.get(model_id), estimate, x.shape[1])
                if model_name in ("OLS", "WLS", "GLS", "GLSAR", "GLM")
                else None
            )
            aliased, aliased_only = _alias_split(
                x, names, scaled, rank, frame_columns, allowed, exposure
            )
            terms = sorted(
                {
                    _term_of(str(n), frame_columns)
                    for n in names
                    if str(n).lower() not in ("const", "intercept")
                }
            )
            models.append(
                {
                    "model": model_name,
                    "columns": int(x.shape[1]),
                    "rank": rank,
                    "condition": None if not _math.isfinite(cond) else cond,
                    "deficient": bool(
                        not aliased_only
                        and (rank < x.shape[1] or dead or cond > __DESIGN_CONDITION_LIMIT__)
                    ),
                    "aliased": aliased if aliased_only else [],
                    "dead": dead,
                    "intercept": intercept,
                    "terms": terms,
                    "names": [str(n) for n in names][:60],
                }
            )
        if not models:
            return None
        bad = next((m for m in models if m["deficient"]), None)
        main = bad or models[-1]
        no_intercept = next((m["model"] for m in models if not m["intercept"]), None)
        aliased = sorted({n for m in models for n in m["aliased"]})
        return {
            **main,
            "aliased": aliased,
            "n_models": len(models),
            "deficient": bad is not None,
            "no_intercept": no_intercept,
        }

    def _intercept_error(design):
        return (
            "the " + str(design["no_intercept"]) + " model has no intercept: no column of its"
            + " design is constant, so the fit is forced through the origin and the coefficient"
            + " of the exposure absorbs the missing constant; add one with"
            + " sm.add_constant(X, has_constant='add') or use a formula, which adds it."
            + " Columns: " + repr(design["names"][:20])
        )

    def _design_error(design):
        cond = design["condition"]
        if design["rank"] < design["columns"] or design["dead"]:
            dead = ", all-zero columns " + repr(design["dead"][:8]) if design["dead"] else ""
            detail = (
                "rank " + str(design["rank"]) + " of " + str(design["columns"]) + " columns"
                + dead
            )
        else:
            detail = "condition number " + format(cond, ".3g") + " above __DESIGN_CONDITION_LIMIT__"
        wide = ""
        if design["columns"] > __DESIGN_WIDE_COLUMNS__:
            wide = (
                " The design has " + str(design["columns"]) + " columns: a categorical with"
                + " hundreds of levels (an identifier such as a player, referee, user or country)"
                + " must not be dummy-coded; cluster the errors on it or aggregate to that unit."
            )
        return (
            "the model's design matrix is rank-deficient or collinear (" + detail
            + "): collinear columns are redundant and make the standard errors meaningless;"
            + " typical cause: dummy columns for every level of a categorical plus an intercept"
            + " (use pd.get_dummies(..., drop_first=True, dtype=float))."
            + wide
            + " Columns: " + repr(design["names"][:20])
        )
"""

FINGERPRINT_SOURCE = """
    def _fingerprint(out, ctx):
        import hashlib as _hashlib

        try:
            digest = _hashlib.sha1()
            digest.update(_json.dumps(list(map(str, out.columns))).encode())
            digest.update(_pd.util.hash_pandas_object(out, index=True).values.tobytes())
            digest.update(_json.dumps(ctx, sort_keys=True, default=str).encode())
            return digest.hexdigest()[:16]
        except Exception:
            return None
"""
