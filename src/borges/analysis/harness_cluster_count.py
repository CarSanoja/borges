"""Cluster-robust errors on too few clusters, checked in full universes only.

A live fertility_religiosity run on 6 Oct 2026 (r_20261006T215037_03c436, before the judge was told
that clustering on a date is indefensible) clustered the errors by the testing date. The 275 women
were tested on 13 dates, and the interaction's p-value fell from 0.15 to 0.0005 with the same
estimate: all six flips of that run came from this option. With few clusters the cluster-robust
variance is biased down and the interval is too narrow. Cameron and Miller (2015, "A Practitioner's
Guide to Cluster-Robust Inference") put "few" anywhere from fewer than 20 to fewer than 50 clusters
depending on the design, so the harness refuses fewer than 20, few in every reading, and leaves the
band above it to the judge. The check reads the fit the reported estimate came from, so it applies
whether the harness or the option's own code asked for the clustering, and it applies to the full
data only, because the smoke run samples rows and can drop small clusters.

An exposure assigned to whole clusters is the other case. A K-12 run (r_20261009T065046_af1a24)
had a curriculum adopted by 5 of 10 schools: the baseline clustered by school and this check
failed it with "use robust errors", which ignore the schools and gave p = 0.004 where clustering
gives 0.20. When the exposure is the same on every row of each cluster the clustering stays, with
t critical values on G - 1 degrees of freedom (use_t=True; the template and the cluster hook ask
for them below SMALL_SAMPLE_CLUSTERS), or the model is fitted on one row per cluster.
"""

from __future__ import annotations

MIN_CLUSTERS = 20
SMALL_SAMPLE_CLUSTERS = 30

CLUSTER_COUNT_SOURCE = """
    def _cluster_count(fit):
        if str(getattr(fit, "cov_type", "")).lower() != "cluster":
            return None
        groups = getattr(fit, "n_groups", None)
        if isinstance(groups, (tuple, list)):
            groups = min(groups) if groups else None
        return int(groups) if groups is not None else None

    def _assigned_by_cluster(fit, exog, index):
        kwds = getattr(fit, "cov_kwds", None)
        groups = kwds.get("groups") if isinstance(kwds, dict) else None
        try:
            codes = _pd.factorize(_np.asarray(groups).ravel())[0]
            column = _np.asarray(exog, dtype=float)[:, index]
        except Exception:
            return False
        if codes.shape[0] != column.shape[0]:
            return False
        frame = _pd.DataFrame({"group": codes, "exposure": column})
        return bool((frame.groupby("group")["exposure"].nunique() <= 1).all())

    def _small_sample_t(fit, groups):
        df = getattr(fit, "df_resid_inference", None)
        return bool(getattr(fit, "use_t", False)) and df is not None and df <= groups - 1

    def _check_few_clusters(estimate):
        if not __FULL_DATA_CHECKS__ or not isinstance(estimate, (int, float)):
            return
        for _, exog, names, model_id in reversed(_designs):
            if model_id in _helpers:
                continue
            index = _exposure_index(_fits.get(model_id), estimate, len(names))
            if index is None:
                continue
            fit = _results.get(model_id)
            groups = _cluster_count(fit)
            if groups is not None and groups < __MIN_CLUSTERS__ and _assigned_by_cluster(
                fit, exog, index
            ):
                if _small_sample_t(fit, groups):
                    return
                raise ValueError(
                    "the exposure is the same on every row of each of the " + str(groups)
                    + " clusters (it was assigned to whole clusters), so errors that ignore the"
                    + " clusters are too narrow, and so is a cluster-robust interval on normal"
                    + " critical values with this few clusters: keep the clustering and use t"
                    + " critical values on " + str(groups - 1) + " degrees of freedom,"
                    + " .fit(cov_type='cluster', cov_kwds={'groups': groups}, use_t=True), or fit"
                    + " one row per cluster (the cluster means)"
                )
            if groups is not None and groups < __MIN_CLUSTERS__:
                raise ValueError(
                    "the errors are clustered on only " + str(groups) + " groups: with fewer than "
                    + str(__MIN_CLUSTERS__) + " clusters the cluster-robust interval is too narrow,"
                    + " so this universe is left out of the analysis instead of counting as a"
                    + " result; cluster on a unit with more groups or use robust errors"
                )
            return
"""
