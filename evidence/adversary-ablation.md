# Adversary ablation

Does the adversary find anything the planner does not? For every completed live run of three
censuses (`evidence/census.md`), `scripts/adversary_ablation.py` splits the garden into the
planner-only arm (universes that use no adversary option) and the universes that hold one. A flip
is credited to the adversary alone only when its twin universe, identical except for the planner's
default at that step, keeps the original verdict. Nothing below is hand-edited; regenerate with

    uv run python scripts/adversary_ablation.py DIR --md OUT --title TITLE

Columns count runs. "Only the adversary finds a flip" means the planner-only arm of that run has no
flipped universe and the adversary's universes do. Each bullet is one flipped universe whose
planner twin keeps the verdict, so a run can appear more than once.

Reading, over three censuses (101 completed runs). In the final census of 5 October (34 completed
runs; red_cards at `5070877`, bank at `6317040`, the rest at `16f02e7`) the adversary added no
run with a flip: the 9 runs that found one found it in the planner's own options too. In 3 runs,
all checkout, an adversary option reversed the verdict on its own, by excluding only the internal
sessions, adjusting for `is_internal`, or excluding internal sessions plus the top 1% of session
lengths. Its planner twin kept SHIP. In the cecf187 census the adversary turned 13 runs that found
a flip into 16, and in 7 of 35 runs at least one of its options reversed the verdict on its own.
Those flips are the classic forks of each literature: a count model on the hurricane deaths
(Poisson or negative binomial, the family of the original paper, against the planner's default
OLS), dropping the demographic controls on the MARP norms model, and a negative binomial with
league-clustered errors on the red cards. In the efe1aa5 census the adversary added no run with a
flip, but reversed the verdict on its own in 3 of 32 runs. Across the three censuses the
adversary is the only source of a flip in 3 of 101 runs, and one of its options reverses the
verdict by itself in 13. The bank verdict survived every adversary option in all three censuses.
The adversary's value is measured, and it is modest: it mostly re-finds forks the planner already
lists, and it rarely adds a flip the planner misses.

## Final census (34 completed of 35, 5 October 2026)

| case | runs | runs with adversary options | planner only finds a flip | full finds a flip | only the adversary finds a flip | runs with an adversary alone flip |
|---|---|---|---|---|---|---|
| bank_marketing_calls | 5 | 5 | 0 | 0 | 0 | 0 |
| checkout_ab | 10 | 9 | 7 | 7 | 0 | 3 |
| hurricanes | 5 | 3 | 2 | 2 | 0 | 0 |
| marp_norms | 5 | 3 | 0 | 0 | 0 | 0 |
| marp_religiosity | 5 | 2 | 0 | 0 | 0 | 0 |
| red_cards | 4 | 2 | 0 | 0 | 0 | 0 |
| **all** | **34** | **24** | **9** | **9** | **0** | **3** |

- `checkout_ab-2.json` (SHIP): Exclude only internal sessions at `filter_internal_and_bots` -> DON'T SHIP
- `checkout_ab-2.json` (SHIP): Exclude only internal sessions at `filter_internal_and_bots` -> DON'T SHIP
- `checkout_ab-2.json` (SHIP): Exclude only internal sessions at `filter_internal_and_bots` -> DON'T SHIP
- `checkout_ab-5.json` (SHIP): Adjust for platform and is_internal at `adjust_covariates` -> DON'T SHIP
- `checkout_blind-2.json` (SHIP): Exclude internal sessions and top 1% of session_seconds at `filter_records` -> DON'T SHIP
- `checkout_blind-2.json` (SHIP): Exclude internal sessions and top 1% of session_seconds at `filter_records` -> DON'T SHIP
- `checkout_blind-2.json` (SHIP): Exclude internal sessions and top 1% of session_seconds at `filter_records` -> DON'T SHIP
- `checkout_blind-2.json` (SHIP): Exclude internal sessions and top 1% of session_seconds at `filter_records` -> DON'T SHIP

## Census at cecf187 (35 runs, 4 October 2026)

| case | runs | runs with adversary options | planner only finds a flip | full finds a flip | only the adversary finds a flip | runs with an adversary alone flip |
|---|---|---|---|---|---|---|
| bank_marketing_calls | 5 | 4 | 0 | 0 | 0 | 0 |
| checkout_ab | 10 | 5 | 8 | 8 | 0 | 2 |
| hurricanes | 5 | 5 | 3 | 4 | 1 | 3 |
| marp_norms | 5 | 1 | 1 | 2 | 1 | 1 |
| marp_religiosity | 5 | 2 | 0 | 0 | 0 | 0 |
| red_cards | 5 | 3 | 1 | 2 | 1 | 1 |
| **all** | **35** | **20** | **13** | **16** | **3** | **7** |

- `checkout_ab-4.json` (SHIP): Exclude very short sessions (<30s) at `step_filter_records` -> DON'T SHIP
- `checkout_blind-5.json` (DON'T SHIP): Keep internal sessions but add internal flag as covariate at `step1_filter_internal` -> SHIP
- `hurricanes-2.json` (NO CLEAR EVIDENCE): Use Poisson regression with robust SE for death counts at `step4_model_estimate` -> FEMININE NAMES DEADLIER
- `hurricanes-3.json` (NO CLEAR EVIDENCE): GLM Negative Binomial with log link at `step_model_estimate` -> FEMININE NAMES DEADLIER
- `hurricanes-5.json` (NO CLEAR EVIDENCE): Poisson regression with robust standard errors at `step4_model_estimation` -> FEMININE NAMES DEADLIER
- `marp_norms-2.json` (DEPENDS ON NORMS): OLS with no demographic controls at `step6_model` -> NO CLEAR EVIDENCE
- `marp_norms-2.json` (DEPENDS ON NORMS): OLS with no demographic controls at `step6_model` -> NO CLEAR EVIDENCE
- `marp_norms-2.json` (DEPENDS ON NORMS): OLS with no demographic controls at `step6_model` -> NO CLEAR EVIDENCE
- `red_cards-1.json` (BIAS DETECTED): Negative binomial with SEs clustered by league country at `step_model_red_card_rate` -> NO CLEAR EVIDENCE

## Census at efe1aa5 (32 completed of 35, 4 October 2026)

| case | runs | runs with adversary options | planner only finds a flip | full finds a flip | only the adversary finds a flip | runs with an adversary alone flip |
|---|---|---|---|---|---|---|
| bank_marketing_calls | 3 | 3 | 0 | 0 | 0 | 0 |
| checkout_ab | 9 | 6 | 7 | 7 | 0 | 1 |
| hurricanes | 5 | 4 | 3 | 3 | 0 | 1 |
| marp_norms | 5 | 3 | 2 | 2 | 0 | 0 |
| marp_religiosity | 5 | 0 | 0 | 0 | 0 | 0 |
| red_cards | 5 | 3 | 2 | 2 | 0 | 1 |
| **all** | **32** | **19** | **14** | **14** | **0** | **3** |

- `checkout_blind-5.json` (SHIP): Exclude internal and trim 1% tails on session_seconds and revenue at `step_filter_records` -> DON'T SHIP
- `hurricanes-5.json` (FEMININE NAMES DEADLIER): Adjust for wind speed only at `step_feature_covariates` -> NO CLEAR EVIDENCE
- `red_cards-5.json` (BIAS DETECTED): Negative binomial regression, no cluster-robust SE at `step_model_red_cards` -> NO CLEAR EVIDENCE
