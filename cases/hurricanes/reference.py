from __future__ import annotations

from borges.cases.models import ReferenceEstimate

REFERENCE_LABEL = "Simonsohn, Simmons and Nelson (2020) specification curve, 1,728 specifications"

SOURCE = (
    "Simonsohn, U., Simmons, J. P. and Nelson, L. D. (2020), Specification curve analysis, "
    "Nature Human Behaviour 4, https://doi.org/10.1038/s41562-020-0912-z. Page numbers below "
    "are PDF pages of the author-hosted copy (9 pages)."
)

FACTS = {
    "specifications": 1728,
    "significant_predicted_direction": 37,
    "median_effect_additional_deaths": 1.56,
    "range_additional_deaths": (-1.0, 12.0),
    "shuffled_samples_with_at_least_37_significant": 425,
    "shuffled_samples": 500,
    "p_share_significant": 0.85,
    "p_median": 0.536,
}

PAGES = {
    "specifications": (
        "p. 4 (Step 1: 'a set of 1,728 reasonable specifications'); Fig. 2 caption, p. 3"
    ),
    "significant_predicted_direction": "p. 4 ('37 responses ... robustness'); p. 6 and Table 2",
    "median_effect_additional_deaths": "Table 2, p. 6 ('1.56 additional deaths', P = 0.536)",
    "range_additional_deaths": "p. 4 ('point estimates range from -1 to +12 additional deaths')",
    "share_test": "Table 2, p. 6 (37 of 1,728, P = 0.850); p. 6 text (425 of 500 shuffles)",
    "most_not_significant": (
        "p. 4 ('a very small minority of all estimates is statistically significant')"
    ),
}


def reference_rows() -> list[ReferenceEstimate]:
    low, high = FACTS["range_additional_deaths"]
    return [
        ReferenceEstimate(
            label="Specification curve median across 1,728 specifications (Table 2, p. 6)",
            estimate=FACTS["median_effect_additional_deaths"],
            significant=False,
        ),
        ReferenceEstimate(label="Specification curve lowest point estimate (p. 4)", estimate=low),
        ReferenceEstimate(label="Specification curve highest point estimate (p. 4)", estimate=high),
    ]


def share_significant() -> float:
    return FACTS["significant_predicted_direction"] / FACTS["specifications"]
