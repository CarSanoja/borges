from __future__ import annotations

VERDICTS = {
    "internal_traffic.exclude_internal": (
        0.92,
        "Employee and QA sessions are test traffic outside the customer population the question "
        "is about; removing them is the standard first check of an online experiment.",
    ),
    "bot_filter.min_2s": (
        0.8,
        "A checkout cannot be completed in under two seconds, so such sessions are automated "
        "traffic; the threshold is a convention that deserves one sentence of justification.",
    ),
    "novelty_window.drop_first_3_days": (
        0.72,
        "Novelty effects fade over the first days of a new interface, so dropping them estimates "
        "the steady state; the cut-off is a judgement but the practice is recognised.",
    ),
    "unit.first_session_per_user": (
        0.78,
        "Randomisation is by user, so analysing one row per user respects the unit of "
        "randomisation; it narrows the sessions counted but not the question.",
    ),
    "model.logit_platform": (
        0.85,
        "Adjusting a randomised comparison for a prognostic covariate improves precision and "
        "keeps the same estimand.",
    ),
}
