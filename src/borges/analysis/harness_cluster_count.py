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
"""

from __future__ import annotations

MIN_CLUSTERS = 20

CLUSTER_COUNT_SOURCE = """
    def _cluster_count(fit):
        if str(getattr(fit, "cov_type", "")).lower() != "cluster":
            return None
        groups = getattr(fit, "n_groups", None)
        if isinstance(groups, (tuple, list)):
            groups = min(groups) if groups else None
        return int(groups) if groups is not None else None

    def _check_few_clusters(estimate):
        if not __FULL_DATA_CHECKS__ or not isinstance(estimate, (int, float)):
            return
        for _, _, names, model_id in reversed(_designs):
            if model_id in _helpers:
                continue
            if _exposure_index(_fits.get(model_id), estimate, len(names)) is None:
                continue
            groups = _cluster_count(_results.get(model_id))
            if groups is not None and groups < __MIN_CLUSTERS__:
                raise ValueError(
                    "the errors are clustered on only " + str(groups) + " groups: with fewer than "
                    + str(__MIN_CLUSTERS__) + " clusters the cluster-robust interval is too narrow,"
                    + " so this universe is left out of the analysis instead of counting as a"
                    + " result; cluster on a unit with more groups or use robust errors"
                )
            return
"""
