from __future__ import annotations

VERDICTS = {
    "storms.keep_all": (
        0.8,
        "Keeping every storm needs no justification for discarding data, though the two "
        "deadliest storms dominate any count model.",
    ),
    "storms.drop_top1": (
        0.65,
        "A milder trim than the original; it still rests on an arbitrary cut-off.",
    ),
    "storms.drop_over_100": (
        0.7,
        "Excluding storms above 100 deaths was proposed by critics of the original paper and "
        "changes the population to ordinary storms.",
    ),
    "femininity.female_binary": (
        0.8,
        "The binary indicator is the plain reading of 'feminine name' and uses the same names.",
    ),
    "femininity.masfem_mturk": (
        0.78,
        "An independent panel scored the same names on the same scale, so it is a "
        "measurement alternative.",
    ),
    "damages.log_2015": (
        0.85,
        "Damage is heavily right-skewed and a log scale is a standard way to model it.",
    ),
    "damages.linear_2013": (
        0.7,
        "The 2013 normalisation is the measure the original paper used; two storms lack it.",
    ),
    "strength.wind": (0.82, "Wind speed is a standard measure of intensity at landfall."),
    "strength.category": (0.78, "The Saffir-Simpson category is a coarse but standard measure."),
    "interaction.damages_only": (
        0.75,
        "A simpler interaction than the original; it keeps the idea that femininity acts "
        "through damage.",
    ),
    "interaction.main_effect": (
        0.8,
        "A main effect is the most direct test of the claim as worded.",
    ),
    "year_control.year_x_damages": (
        0.78,
        "Deaths per unit of damage plausibly changed over six decades of warnings.",
    ),
    "year_control.post1979_x_damages": (
        0.72,
        "A regime indicator for the naming change is a transparent era control.",
    ),
    "model.ols_log1p": (
        0.7,
        "A log-linear model is a common alternative for skewed counts, with a retransformation "
        "caveat for the effect in deaths.",
    ),
}
