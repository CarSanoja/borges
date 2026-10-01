from __future__ import annotations

from borges.analysis.schemas import PlannedOption, PlannedStep, PlannerOutput, ProposedOption

ESTIMAND = (
    "Difference in conversion probability between the new and the old checkout, "
    "treatment minus control, in percentage points, over checkout sessions of genuine "
    "customers in the 14-day experiment window."
)

KOHAVI = "Kohavi, Tang & Xu (2020), Trustworthy Online Controlled Experiments, Cambridge UP"


def planner_output() -> PlannerOutput:
    return PlannerOutput(
        estimand=ESTIMAND,
        steps=[
            PlannedStep(
                id="internal_traffic",
                title="Internal traffic",
                kind="filter",
                description=(
                    "Decide whether employee and QA test sessions (is_internal) stay in "
                    "the analysis population."
                ),
                options=[
                    PlannedOption(
                        id="keep_all",
                        label="Keep all sessions",
                        rationale=(
                            "The experiment was randomised over every visitor, so analysing "
                            "everyone is the pre-registered intent-to-treat population."
                        ),
                        spec="No rows removed.",
                        is_default=True,
                    ),
                    PlannedOption(
                        id="exclude_internal",
                        label="Exclude internal accounts",
                        rationale=(
                            "Employee and QA sessions place test orders, are not customers "
                            "and are not covered by the question. Their share is unbalanced "
                            "across arms, so they can create a lift the checkout did not cause."
                        ),
                        spec="Drop rows where is_internal is true.",
                        source=KOHAVI + ", ch. 3 and 21 (filter internal traffic and bots)",
                    ),
                ],
            ),
            PlannedStep(
                id="bot_filter",
                title="Bot filter",
                kind="filter",
                description="Decide whether sessions too short to be human are removed.",
                options=[
                    PlannedOption(
                        id="none",
                        label="No bot filter",
                        rationale=(
                            "Bots are assigned at random like everyone else, so they only "
                            "dilute both arms equally and the difference stays unbiased."
                        ),
                        spec="No rows removed.",
                        is_default=True,
                    ),
                    PlannedOption(
                        id="min_2s",
                        label="Drop sessions under 2 seconds",
                        rationale=(
                            "Sessions shorter than two seconds cannot complete a checkout and "
                            "are the usual signature of automated traffic; removing them "
                            "sharpens the denominator."
                        ),
                        spec="Keep rows where session_seconds >= 2.",
                        source=(
                            "IAB/MRC Invalid Traffic Detection and Filtration Guidelines "
                            "Addendum (2020); ABC bot-filtering guidance"
                        ),
                    ),
                ],
            ),
            PlannedStep(
                id="novelty_window",
                title="Novelty window",
                kind="filter",
                description="Decide whether the first days, when users react to novelty, count.",
                options=[
                    PlannedOption(
                        id="all_days",
                        label="Use all 14 days",
                        rationale=(
                            "Using the full window keeps the pre-registered sample size and "
                            "avoids a post-hoc choice of cut-off."
                        ),
                        spec="No rows removed.",
                        is_default=True,
                    ),
                    PlannedOption(
                        id="drop_first_3_days",
                        label="Drop days 0-2",
                        rationale=(
                            "A new interface attracts curiosity clicks that fade within days, "
                            "so early days overstate the steady-state effect. Dropping the "
                            "ramp-up estimates the lasting effect."
                        ),
                        spec="Keep rows where day >= 3.",
                        source=(
                            "Hohnhold, O'Brien & Tang (2015), Focusing on the Long-term, "
                            "KDD; " + KOHAVI + ", ch. 3 (novelty and primacy effects)"
                        ),
                    ),
                ],
            ),
            PlannedStep(
                id="unit",
                title="Unit of analysis",
                kind="transform",
                description=(
                    "Variants are assigned per user, but users return up to four times: "
                    "decide whether the unit is the session or the user."
                ),
                options=[
                    PlannedOption(
                        id="sessions",
                        label="All sessions",
                        rationale=(
                            "Conversion rate is defined per session by the product team, "
                            "and every session is an opportunity to buy."
                        ),
                        spec="No rows removed.",
                        is_default=True,
                    ),
                    PlannedOption(
                        id="first_session_per_user",
                        label="First session per user",
                        rationale=(
                            "Randomisation is by user, so repeated sessions of the same user "
                            "are not independent. One row per user matches the randomisation "
                            "unit and removes within-user dependence."
                        ),
                        spec="Keep the earliest session (by day, then session_id) of each user.",
                        source=(
                            "Deng, Lu & Litz (2017), Trustworthy Analysis of Online A/B Tests, WSDM"
                        ),
                    ),
                ],
            ),
            PlannedStep(
                id="model",
                title="Statistical model",
                kind="model",
                description="Estimate the conversion lift and its uncertainty.",
                options=[
                    PlannedOption(
                        id="two_prop_z",
                        label="Two-proportion z-test",
                        rationale=(
                            "The textbook test for a randomised binary outcome; it needs no "
                            "model assumptions beyond large samples."
                        ),
                        spec=(
                            "Lift in percentage points, treatment minus control, with a "
                            "normal-approximation 95% CI and a two-sided pooled z-test p-value."
                        ),
                        is_default=True,
                    ),
                    PlannedOption(
                        id="logit_platform",
                        label="Logistic regression with platform",
                        rationale=(
                            "Adjusting for a prognostic covariate such as platform improves "
                            "precision without biasing a randomised comparison."
                        ),
                        spec=(
                            "Logit of converted on treatment and C(platform); the treatment "
                            "effect is the average marginal effect in percentage points, with "
                            "its delta-method CI and p-value."
                        ),
                        source=(
                            "Lin (2013), Agnostic notes on regression adjustments, "
                            "Annals of Applied Statistics"
                        ),
                    ),
                ],
            ),
        ],
    )


def adversary_proposals() -> list[ProposedOption]:
    return [
        ProposedOption(
            step_id="model",
            id="adv_ols_cluster_user",
            label="Linear probability model, SEs clustered by user",
            rationale=(
                "Variants are assigned per user and users return several times, so session "
                "rows are correlated; standard errors that ignore this are too small. A "
                "user-clustered estimator is the standard correction."
            ),
            spec=(
                "OLS of converted on treatment with cluster-robust standard errors grouped by "
                "user_id; report the coefficient in percentage points, its CI and p-value."
            ),
            source=(
                "Abadie, Athey, Imbens & Wooldridge (2023), When Should You Adjust "
                "Standard Errors for Clustering?, QJE"
            ),
        ),
        ProposedOption(
            step_id="bot_filter",
            id="adv_engaged_only",
            label="Keep only engaged sessions (30 seconds or more)",
            rationale=(
                "Short sessions are low-intent browsing, so restricting to engaged sessions "
                "isolates users who actually considered buying."
            ),
            spec="Keep rows where session_seconds >= 30.",
            source=None,
        ),
    ]
