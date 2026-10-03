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

DESIGN_SOURCE = """
    _designs = []

    def _install_design_probe():
        try:
            from statsmodels.base import model as _sm_model
        except Exception:
            return
        original = _sm_model.Model.__init__

        def probed(self, *args, **kwargs):
            original(self, *args, **kwargs)
            try:
                if self.exog is not None:
                    _designs.append((type(self).__name__, self.exog, list(self.exog_names)))
            except Exception:
                pass

        _sm_model.Model.__init__ = probed

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

    def _design_payload(frame_columns):
        models = []
        for model_name, exog, names in _designs:
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
                        rank < x.shape[1] or dead or cond > __DESIGN_CONDITION_LIMIT__
                    ),
                    "dead": dead,
                    "terms": terms,
                    "names": [str(n) for n in names][:60],
                }
            )
        if not models:
            return None
        bad = next((m for m in models if m["deficient"]), None)
        main = bad or models[-1]
        return {**main, "n_models": len(models), "deficient": bad is not None}

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
        return (
            "the model's design matrix is rank-deficient or collinear (" + detail
            + "): collinear columns are redundant and make the standard errors meaningless;"
            + " typical cause: dummy columns for every level of a categorical plus an intercept"
            + " (use pd.get_dummies(..., drop_first=True, dtype=float) or drop the constant)."
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
