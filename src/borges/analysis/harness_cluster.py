"""Clustered standard errors, fitted by the harness for a model option that asks for them.

A model option may carry a cluster column (Option.cluster_by) that the rendered step passes to the
main as `cluster_unit`. The option's code is the code of an option that passed the code guard, as it
was written; the harness, not the code, adds the clustering. Every
statsmodels OLS, WLS, GLM, Logit, Probit, Poisson or NegativeBinomial that the step then fits is
fitted with cov_type="cluster", the groups being the values of that column on the rows the model
uses, whatever covariance the code asked for. A step that fits no such model, or whose rows cannot
be matched to the data, fails with a reason instead of reporting errors that are not clustered.
"""

from __future__ import annotations

CLUSTER_MODELS = (
    ("statsmodels.regression.linear_model", ("OLS", "WLS")),
    ("statsmodels.genmod.generalized_linear_model", ("GLM",)),
    ("statsmodels.discrete.discrete_model", ("Logit", "Probit", "Poisson", "NegativeBinomial")),
)

CLUSTER_SOURCE = """
    _clustered = []

    def _cluster_groups(model, frame, unit):
        rows = model.exog.shape[0]
        labels = getattr(model.data, "row_labels", None)
        if (
            labels is not None
            and len(labels) == rows
            and _pd.Index(labels).is_unique
            and frame.index.is_unique
            and _pd.Index(labels).isin(frame.index).all()
        ):
            column = frame.loc[list(labels), unit]
        elif len(frame) == rows:
            column = frame[unit]
        else:
            raise ValueError(
                "cannot cluster the errors by " + repr(unit) + ": the model uses " + str(rows)
                + " rows that cannot be matched to the " + str(len(frame)) + " rows of the data;"
                + " fit the model on a DataFrame that keeps the row index"
            )
        if column.isna().any():
            raise ValueError(
                "cannot cluster the errors by " + repr(unit) + ": it is missing in "
                + str(int(column.isna().sum())) + " rows the model uses"
            )
        return _pd.factorize(column)[0]

    def _install_cluster_hook(unit, frame):
        if unit is None:
            return
        if unit not in frame.columns:
            raise ValueError("cannot cluster the errors by " + repr(unit) + ": no such column")
        import importlib as _importlib

        def _wrap(original):
            def fit(self, *args, **kwargs):
                groups = _cluster_groups(self, frame, unit)
                kwargs["cov_type"] = "cluster"
                kwargs["cov_kwds"] = {"groups": groups}
                if len(_np.unique(groups)) < __SMALL_SAMPLE_CLUSTERS__:
                    kwargs["use_t"] = True
                _clustered.append(type(self).__name__)
                return original(self, *args, **kwargs)

            return fit

        for module, names in __CLUSTER_MODELS__:
            loaded = _importlib.import_module(module)
            for name in names:
                cls = getattr(loaded, name)
                cls.fit = _wrap(cls.fit)

    def _check_clustered(unit):
        if unit is not None and not _clustered:
            raise ValueError(
                "the option asks for errors clustered by " + repr(unit) + ", but the step fitted"
                + " no statsmodels OLS, WLS, GLM, Logit, Probit, Poisson or NegativeBinomial"
                + " model, the families that take a cluster covariance"
            )
"""
