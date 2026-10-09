# Held-out test: the published analysis of the vote

The fertility cases were used to develop the published-analysis feature, so a result on them
says how well Borges does on the data it was tuned on. This file reports a test on data it had
never seen, with the success rule written down before the first run.

## The case

`evidence/held-out/cases/fertility_vote`: Durante et al. (2013), Study 2, 502 women, the vote for Obama or
Romney, a logistic regression on fertility, relationship status and their product. The fertility
cases use Study 1, a different sample, a 1-9 outcome and OLS. Borges is given the published
analysis in plain words and asked how fragile it is.

The ground truth was computed before any run. The port of Steegen et al.'s multiverse
(`evidence/held-out/durante_study2/steegen_multiverse.py vote`) reproduces the paper: an interaction of -1.6230,
p .0038, n 303, against the published b = -1.62, Wald(1) = 8.35, p = .004, with 131 + 172 women,
and the four cell percentages match. Of the ten single changes in Steegen's grid, two flip it
(the certainty exclusion, p .1126, and the participant's own next-onset date, p .1135). Outside
the grid, married only gives p .0524 and both windows two days earlier p .1360.

## The rule, written before the first run

Frozen commit `2345f04`, five attempts, every attempt counted. Success needed both:

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

The data of Study 2 come from an OSF project that states no licence, so both Study 2 cases live
here rather than among the curated cases, and their data are downloaded by
`durante_study2/prepare.py`, never committed. (The first commit of the vote case, `2345f04`,
included the file when the runs were made; it was removed from the history on 7 October, before
the repository was published.)

## Development on the vote case, 7 October

Twelve further live runs (6 to 17), each against a hypothesis written down before it, with the
fix that followed. The hypotheses and costs were kept in the team's working log, which is not
part of this repository; the defects, in order:

- The step-by-step code dropped the two hand-set participants (n 301), coded fertility as -1/+1
  (estimate halved), kept days 15-16 as low fertility (n 344) or dated the next onset from the
  participant's estimate (n 279), while the plan's specs were right. A check of the specs cannot
  see that. **Fix:** the whole analysis is written again as one script by a second model, twice and
  independently, and run on the raw data; two scripts that agree are the reference. Asked for the
  whole analysis in one script, that model wrote the exact published cell in 4 of 5 attempts and
  never a wrong number; the coder model got 0 of 5. A reference equal to the baseline confirms
  it; a different one sends the steps that depart to repair, and a repair that does not reach the
  reference is undone and reported.
- In run 14 the first script was right, the second copied the baseline's mistake, and a vote
  that counted the baseline confirmed the wrong starting point. **Fix:** the baseline never votes;
  a third script is written when the first two disagree.
- A logistic fit with a separated cell (-36.6, interval ±43,000) was reported as the smallest
  flip. **Fix:** such fits are set aside as not estimable.
- The code reviewer dropped "married only" and "dating counts as committed" as estimand changes
  by comparing them with the default's grouping, after the judge had accepted them. **Fix:** for an
  accepted option the estimand is the judge's call; a reviewer verdict must quote the option's own
  spec.
- The split-half check refused a sound interval because the halves of a small sample were
  separated. **Fix:** the check abstains when a half cannot be estimated.

## Development runs 15 to 41, 7 October

Twenty-seven more live runs of the vote case, three at a time, each round against a hypothesis
written down before it in the team's working log (not part of this repository), about $0.06 to
$0.11 each. They are development
results, not held out.

| Outcome | Runs |
|---|---|
| Starting point exact, or repaired to the exact cell (-1.6230, n 303) | 11: 17, 19, 20, 24, 27, 29, 32, 33, 36, 40, 41 |
| Starting point wrong, reported as "does not match" two independent implementations | 9: 16, 18, 21, 25, 26, 28, 34, 35, 37 |
| Run failed before a result | 7: 15, 22, 23, 30, 31, 38, 39 |

No run reported a wrong starting point as checked. Every reported flip from a checked starting
point that was recomputed with independent code matched to the fourth decimal (runs 17, 19, 20,
24, 27, 32, 33, 36, 40, 41). Two reported flips were the starting point with one group coded the
other way (runs 28 and 29) and one adjusted for WorkerID cut into thirds (run 40); both kinds are
now set aside or refused. Every defect found, and its fix:

- A coder set the two hand-set days and then overwrote the whole column (28), or created the
  column only for those two rows by WorkerID, through a selector variable or by position (30, 31,
  34, 38). **Fix:** two code checks, and the harness fails a step whose produced column is missing
  in 95% of the rows it keeps.
- A filter computed the cycle day and did not pass it on, so later coders were told it did not
  exist (34, 35). **Fix:** a name a filter computes and a later step reads is added to what the
  filter produces.
- The model step built its fertility indicator from a range of days inside its own spec (39).
  **Fix:** such a plan goes back to the planner.
- A result equal to the starting point with its sign reversed on the same rows and p-value (28,
  29). **Fix:** set aside as the same analysis, not a flip.
- The repair of the starting point could not localise the rows it lost (25, 26, 28) or a reversed
  coding (37). **Fix:** it is shown which raw rows each fit keeps, after which step the chain loses
  them and what they hold there; fixes that do not close the gap are dropped one by one; and when
  single repairs fail, every default step is rewritten from the reference script and kept only if
  it then reproduces it. Replayed live on run 37's plan, the rewrite gave the exact cell. Runs 36
  and 41 were repaired this way from n 302 to n 303.

No commit met the bar for freezing (exact or repaired in at least two of three, and no failed
run, in one round): the last round, 39 to 41, had two exact or repaired and one failure, whose
cause is fixed in the final commit but not yet run live. The held-out test below has not been run.

## The next held-out test

`evidence/held-out/cases/fertility_social`: the published analysis of social conservatism on the
same sample. Its answer was computed and its rule written in its README before any run.

**Frozen commit: `3410f7b`**, named here before the first attempt, 09 October 2026, 07:11 UTC. Five attempts run live
on Nebius Token Factory with the ConTree backend, memory off so no attempt reuses another's
code or verdicts, and no code change until all five are counted. The results follow below as
they come, pass or fail.

### Result: failed (9 October 2026, five attempts at `3410f7b`, $0.55 in all)

| Attempt | Run | Starting point | Smallest flip |
|---|---|---|---|
| 1 | r_20261009T071159_5f1d22 | +1.2425, p .0005, n 303: the published cell | Three changes (married only as committed, adjust for the three religiosity items, HC3 errors): +0.7295, p .0567, n 303, reproduced |
| 2 | r_20261009T071201_8c331b | +0.4920, p .0246, n 303: wrong, the scale was built with Abortion not reversed; the report says the starting point could not be confirmed | From the wrong starting point: married only and a narrower window, +0.3085, p .2084 |
| 3 | r_20261009T071203_783130 | none: the run failed | none |
| 4 | r_20261009T071205_467cac | the published cell | none: the plan offered no alternative for any step (5 universes) |
| 5 | r_20261009T071207_1fb342 | the published cell | none in 12 universes; the plan did not offer the coding that flips (dating women as committed) |

- (a) the published starting point in at least 4 of 5: **3 of 5. Fails.**
- (b) no wrong starting point reported as checked: **5 of 5.** Attempt 2's report says its starting
  point could not be confirmed.
- (c) a confirmed smallest flip in at least 3 of 5: **at most 1** (attempt 1; attempt 2 starts
  from a wrong cell, and 3, 4 and 5 report none). **Fails.**

The user-analysis path does not pass its held-out test. What the five attempts show:

- The failed run is a harness fault: the check that names the collinear columns of a design
  crashed on an empty null space (`zero-size array to reduction operation maximum`).
- Attempts 1, 4 and 5 started from the published cell, yet their reports say it "could not be
  confirmed" or "does not match": the independent implementations agree on the estimate, the
  p-value and n, and differ only in the third decimal of the interval (+0.5443 against +0.5471),
  which the comparison counted as a disagreement.
- Two plans in five did not offer the alternatives that flip the published cell (the coding of
  dating women, the fertility windows, the cycle-day count), so no flip could be found.

These are recorded as found. Fixes made after this count do not change it, and the next held-out
claim needs a new case.
