# Held-out test: the published analysis of the vote

The fertility cases were used to develop the published-analysis feature, so a result on them
says how well Borges does on the data it was tuned on. This file reports a test on data it had
never seen, with the success rule written down before the first run.

## The case

`cases/fertility_vote`: Durante et al. (2013), Study 2, 502 women, the vote for Obama or
Romney, a logistic regression on fertility, relationship status and their product. The fertility
cases use Study 1, a different sample, a 1-9 outcome and OLS. Borges is given the published
analysis in plain words and asked how fragile it is.

The ground truth was computed before any run. The port of Steegen et al.'s multiverse
(`cases/fertility_vote/steegen_multiverse.py`) reproduces the paper: an interaction of -1.6230,
p .0038, n 303, against the published b = -1.62, Wald(1) = 8.35, p = .004, with 131 + 172 women,
and the four cell percentages match. Of the ten single changes in Steegen's grid, two flip it
(the certainty exclusion, p .1126, and the participant's own next-onset date, p .1135). Outside
the grid, married only gives p .0524 and both windows two days earlier p .1360.

## The rule, written before the first run

Frozen commit `c009f7a`, five attempts, every attempt counted. Success needed both:

- (a) the baseline reproduces the published cell (-1.62 within 0.01, n 303) in at least 4 of 5;
- (c) a flip by a single change, whose refit matches, in at least 4 of 5.

If a defect showed up, it would not be fixed and re-run under the same name: the case would stop
being held out and the result would be reported as it came.

## Result: the rule failed

| Attempt | Run | Baseline | Smallest flip | Universes (failed) | Cost |
|---|---|---|---|---|---|
| 1 | `r_20261007T044636_9f1a2b` | run failed | none | 0 | $0.0618 |
| 2 | `r_20261007T044641_82617e` | -1.5901, p .0047, n 301: not the published cell | none | 5 (0) | $0.0886 |
| 3 | `r_20261007T044646_d46fb2` | -1.6230, p .003848, n 303 | married only: -1.1046, p .05236, one change, reproduced | 14 (3) | $0.0798 |
| 4 | `r_20261007T044917_ee71f6` | -1.6230, p .003848, n 303 | a 10-17 / 20-28 window plus married only: -0.8122, p .2492, n 182, two changes | 13 (6) | $0.1024 |
| 5 | `r_20261007T044923_0c3469` | -1.6230, p .003848, n 303 | adding attitude items as covariates: -0.7338, p .2644, one change, flagged as an estimand change | 12 (4) | $0.0677 |

(a) held in 3 of 5 and (c) in 2 of 5, or 1 of 5 counting only a flip of the same estimand. Both
fall short of 4 of 5. The five attempts cost $0.40.

What each failure was:

- **Attempt 1.** The coder wrote the default filter as "label every row low, mark the high window
  high, keep the rows not labelled low", which keeps only the 131 women at high fertility. The
  model step caught the symptom (the fertility indicator was the same in every row) and refused
  to fit, but the repair it triggers reaches only the step just before the model. Here that step
  coded relationship status, while the fault was two steps earlier.
- **Attempt 2.** The first step computed the cycle day, including the two participants whose day
  the original authors set by hand. The second step computed the cycle day again from the dates
  and overwrote it, so those two rows became missing and were dropped. Neither the fidelity check
  nor the code reviewer noticed, and the run reported the 301-row result as the published
  analysis.
- **Attempts 4 and 5, failed universes.** The relationship step built its indicator on a fresh
  0..n-1 index and assigned it with masks indexed by the data frame. After a filter that left gaps
  in the index, this raised an indexing error, so all four universes with the certainty exclusion
  failed. That exclusion is the one change in Steegen's grid that Borges did propose.

## What it means

On data it was not developed on, Borges started from the published analysis in 3 of 5 runs and
found a defensible single-change flip in 1 to 2 of 5. When it did, the flip was the one computed
in advance (married only, p .0524). The failures are defects in how steps hand data to each
other, not in the search or the statistics. From here on this is a development case: the fixes
were made with these runs in view, so any later result on it is not held out. The held-out claim
moves to a new case that no fix has been tuned on.
