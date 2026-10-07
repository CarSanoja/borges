# Fertility and social conservatism: how fragile is the published analysis?

A live-only, held-out case. Borges is given a published analysis it was not developed on and asked
how fragile it is. What is held out is the analysis: the outcome (a 1-7 scale built from five
items, three of them reversed), the model (OLS) and the effect. What is not held out is the sample:
these are the 502 women of the vote case, which was used for development on 7 October 2026, so the
cycle-day arithmetic and the relationship coding are the same. Results on this case are reported
with that limit.

## Data

Durante, Rae and Griskevicius (2013), *The fluctuating female vote*, Psychological Science 24(6),
Study 2, from the raw data Steegen et al. (2016) published on OSF (https://osf.io/zj68b/) with the
original author's permission. The OSF project states no licence, so the data are not in this
repository: `../../durante_study2/prepare.py` downloads the file, checks its SHA-256 and writes
`data.parquet` (git-ignored).

## The analysis Borges starts from

`case.json` field `analysis`, the published analysis of social conservatism as Steegen et al.
reconstructed it (cell NMO1, F1, R1, ECL1, EC1 of their grid): the mean of Marriage,
RestrictAbortion and the reversed Abortion, StemCell and Marijuana items; the cycle day from the
last two period dates, with the two hand-set days of the original file; high fertility days 7-14,
low 17-25; single is relationship answers 1 and 2; no other exclusion; OLS of the scale on
fertility, relationship status and their product.

## The answer, computed before any run

`../../durante_study2/steegen_multiverse.py social`:

- The published cell: interaction +1.2425, p .0005, n 303, the paper's F(1, 299) = 12.26.
- Steegen's grid: 103 of 210 combinations give p < .05. Of the ten single changes from the
  published cell, one loses significance: counting dating women as committed (single is answer 1
  only), +0.5270, p .1789, n 303.
- Outside the grid: both fertility windows two days earlier (5-12 and 15-23) give p .1002, n 317;
  married women only as committed gives p .0022 and holds.

## The rule, written before the first run

Five attempts at one frozen commit, every attempt counted, no fix made while looking at them. The
frozen commit is named in `evidence/held-out.md` when the first attempt starts. Success needs all
three:

- (a) the starting point is the published cell (+1.2425 within 0.01, n 303), directly or after a
  repair the report states, in at least 4 of 5;
- (b) no attempt reports a wrong starting point as checked: whenever the "Starting point" line says
  it matches independent implementations or was repaired to match them, the estimate is the
  published cell; 5 of 5;
- (c) in at least 3 of 5, a reported smallest flip whose refit matches, made of changes the judge
  accepted, and confirmed by recomputing it with code written for this check; and in no attempt a
  flip from a fit that cannot be estimated.

If an attempt finds no flip, that is wrong by the grid above, and it counts against (c).

## Reproduce

```
uv run python evidence/held-out/durante_study2/prepare.py
uv run python evidence/held-out/durante_study2/steegen_multiverse.py social
BORGES_CASES_DIR=evidence/held-out/cases uv run borges run --case fertility_social --llm nebius
```
