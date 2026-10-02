from __future__ import annotations

VERDICTS = {
    "religiosity.mean_7_items": (
        0.82,
        "Averaging the seven graded items is a common measurement of religiosity that omits the "
        "two binary items; the construct is unchanged.",
    ),
    "religiosity.self_identification": (
        0.7,
        "A single self-identification item is widely used, though it is a coarser measure of the "
        "same construct.",
    ),
    "religiosity.importance_items": (
        0.64,
        "Importance of religion captures salience rather than belief or practice, so it narrows "
        "the construct; defensible with a sentence of justification.",
    ),
    "wellbeing.items_without_sexual_satisfaction": (
        0.78,
        "One item is missing for participants who did not disclose it, so dropping it is a "
        "reasonable handling of the item-level missingness.",
    ),
    "wellbeing.mean_of_subscales": (
        0.8,
        "Weighting the physical, psychological and social facets equally is a standard way of "
        "scoring the same well-being scale.",
    ),
    "wellbeing.general_items": (
        0.66,
        "Two general items measure well-being directly but cover less of the scale than the "
        "full item set.",
    ),
    "norms.country_mean": (
        0.74,
        "Cultural norms are a property of a country, so aggregating the perception to the country "
        "mean matches the construct; it changes the level at which the norm varies.",
    ),
    "exclusions.attention_check_passed": (
        0.84,
        "Excluding inattentive respondents is a standard data-quality rule applied before "
        "modelling.",
    ),
    "covariates.demographics": (
        0.88,
        "Age, gender, socio-economic status and education relate to both religiosity and "
        "well-being; adjusting for them is standard.",
    ),
    "covariates.demographics_gdp": (
        0.8,
        "Country wealth differs across the 24 countries and relates to both variables; adding "
        "GDP to the demographics is a common specification.",
    ),
    "scaling.within_country_z": (
        0.76,
        "Centring within country isolates the within-country relation; it answers the same "
        "question on a different scale and is a recognised choice.",
    ),
    "model.ols_pooled": (
        0.82,
        "A pooled regression with robust errors is the simple baseline many teams used.",
    ),
    "model.ols_country_fe": (
        0.86,
        "Country fixed effects absorb country differences without distributional assumptions and "
        "keep the same estimand.",
    ),
    "model.multilevel_slope": (
        0.84,
        "A multilevel model with random country slopes is the standard way to let the relation "
        "vary by country.",
    ),
}
