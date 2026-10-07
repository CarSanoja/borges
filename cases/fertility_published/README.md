# Fertility and religiosity: how fragile is the published analysis?

A live-only case. It uses the same data, question and rule as `cases/fertility_religiosity`, and
adds one thing: the analysis behind the published result, which Borges keeps as its starting point
and tries to reverse with the smallest defensible change. This is what a researcher does with
Borges when they bring their own analysis: the question is how fragile that analysis is, not what
the best analysis would be. Nothing in this directory was produced by a model except the recording.

## The analysis Borges starts from

`case.json` field `analysis`, in plain words, as Steegen et al. (2016) reconstructed Durante et
al. (2013), Study 1 (the cell F1, NMO1, R1, ECL1, EC1 of their Table 1): religiosity is the mean
of the answered religiosity items; the cycle day is 28 minus the days from testing to a next onset
computed from the last two period dates; high fertility is cycle days 7 to 14 and low fertility
17 to 25, other days dropped; single is relationship answers 1 and 2 and committed 3 and 4; no
other exclusion; OLS with classical standard errors. On these data that gives 2.3834, p = .012,
n = 163, and `cases/fertility_religiosity/steegen_multiverse.py` reproduces it.

The text gives no hint of which changes matter. Borges is not told Steegen's grid.

## How the starting point is protected

- The planner is asked to make the analysis the default path, implemented as written.
- A second model (Ultra) compares the analysis with the default specs before anything runs and
  lists what differs; the planner fixes those, twice at most, and what still differs becomes a
  caveat of the report (`src/borges/analysis/planner_fidelity.py`).
- The defensibility judge still scores the defaults, but cannot replace them: a choice of the
  user's analysis that the judge disputes stays the starting point and the report says so.

## What Borges found

The live recording (`recorded-live/`, 7 October 2026, run `r_20261007T035352_3cba38`, ConTree,
$0.080) starts from 2.3834 [0.5312, 4.2356], p .012, n 163, the published result. The fidelity
check caught one deviation first (the plan's mean counted unanswered items as 0) and the planner
fixed it. The smallest flip is one change: committed = married only (relationship answer 4
against 1 to 3), which gives NO CLEAR EVIDENCE, 0.8642 [-1.1754, 2.9037], p .4039, n 163. A
refit from the raw data gives the same numbers, and `borges reproduce --case fertility_published
--source live --universe u_f90ae92878` re-executes it: MATCH.

An earlier run from the same analysis (`r_20261007T033617_784e1b`, local backend) found a
different single change: single = not dating and committed = engaged or married, with dating
women left out, which gives 1.7793, p .1218, n 129. That is exactly Steegen et al.'s R3 cell.

Both flips are in how relationship status is coded, the decision Steegen et al. found to matter
most. Borges did not propose the other forks of their grid that also flip the result (the reported
cycle length, other windows, excluding women unsure of their dates), so it reports a smallest
flip, not the whole fragile region. See `evidence/head-to-head.md` for the comparison with
Steegen's grid and with twelve independent persona analysts, none of whom reproduced the published
analysis.

## Data

The same file as `cases/fertility_religiosity/data.parquet` (identical sha256); see that case's
README for the source, licence (ODC-By 1.0) and how to regenerate it.
