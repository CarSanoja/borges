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
DESIGN_ROWS_KEPT = 2000
DESIGN_MEANS_KEPT = 20

DESIGN_SOURCE = """
    _designs = []
    _fits = {}
    _offsets = {}
    _weights = {}
    _results = {}
    _helpers = set()
    _rows = {}

    def _inside_another(model):
        frame = _sys._getframe(2)
        while frame is not None and "statsmodels" in frame.f_code.co_filename:
            owner = frame.f_locals.get("self")
            if owner is not None and owner is not model:
                return True
            frame = frame.f_back
        return False

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
                    if _inside_another(self):
                        _helpers.add(id(self))
                    _record_endog(self)
                    labels = getattr(getattr(self, "data", None), "row_labels", None)
                    if labels is not None and len(labels) <= __DESIGN_ROWS_KEPT__:
                        endog = _np.asarray(self.endog, dtype=float).ravel()
                        weights = _np.arange(1, endog.shape[0] + 1, dtype=float)
                        _rows[id(self)] = ([int(v) for v in labels], float(endog @ weights))
            except Exception:
                pass

        def fitted(self, model, params, *args, **kwargs):
            results(self, model, params, *args, **kwargs)
            try:
                _fits[id(model)] = _np.asarray(params, dtype=float).ravel()
                _results[id(model)] = self
                _offsets[id(model)] = any(
                    getattr(model, name, None) is not None for name in ("offset", "exposure")
                )
                _weights[id(model)] = _weight_array(model)
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
            found = _exposure_index(_fits.get(model_id), estimate, x.shape[1])
            hit = found is not None
            family = getattr(_endogs.get(model_id), "family", None)
            models.append(
                {
                    "reported": hit,
                    "helper": model_id in _helpers,
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
                    "exposure": _term_of(str(names[found]), frame_columns) if hit else None,
                    "exposure_binary": bool(set(_np.unique(x[:, found])) <= {0.0, 1.0})
                    if hit
                    else None,
                    "exposure_sd": float(_np.std(x[:, found])) if hit else None,
                    "offset": _offsets.get(model_id),
                    "exposure_weighted": hit and _same_values(_weights.get(model_id), x[:, found]),
                    "family": type(family).__name__,
                    "link": type(getattr(family, "link", None)).__name__,
                    "endog_levels": _endog_levels(model_id),
                    "cov_type": str(getattr(_results.get(model_id), "cov_type", "") or "") or None,
                    "names": [str(n) for n in names][:60],
                    "rows": (_rows.get(model_id) or (None, None))[0],
                    "endog_check": (_rows.get(model_id) or (None, None))[1],
                    "means": {
                        str(names[i]): round(float(x[:, i].mean()), 6)
                        for i in range(min(x.shape[1], __DESIGN_MEANS_KEPT__))
                    },
                }
            )
        if not models:
            return None
        own = [m for m in models if not m.pop("helper")] or models
        reported = [m for m in own if m.pop("reported")]
        bad = next((m for m in own if m["deficient"]), None)
        main = bad or (reported or own)[-1]
        no_intercept = next((m["model"] for m in own if not m["intercept"]), None)
        aliased = sorted({n for m in own for n in m["aliased"]})
        return {
            **main,
            "aliased": aliased,
            "n_models": len(models),
            "deficient": bad is not None,
            "no_intercept": no_intercept,
        }
"""
