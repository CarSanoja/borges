# Fertility and the vote: how fragile is the published analysis?

A live-only development case. It was the held-out test of 7 October 2026: added after the code it
ran on was frozen, five attempts, every one reported in `evidence/held-out.md`. It failed its
preregistered rule, and the fixes since were made with its runs in view, so later results on it are
not held out; the held-out claim moved to `../fertility_social`. Borges had not been developed on
these data before: the fertility cases use Study 1 of the same paper; this is Study 2, a different
sample, a binary outcome and a logistic model. Nothing in this directory was produced by a model.

## Data

Durante, Rae and Griskevicius (2013), *The fluctuating female vote*, Psychological Science 24(6),
Study 2: 502 women surveyed online before the 2012 US presidential election. Steegen, Tuerlinckx,
Gelman and Vanpaemel (2016) published the raw data on OSF (https://osf.io/zj68b/); their supplement
says the original author gave them permission to make the data publicly available. The OSF project
states no licence, so the data are not in this repository and the case is not among the curated
cases of the demo: `../../durante_study2/prepare.py` downloads the file, checks its SHA-256 and
writes `data.parquet` (git-ignored) unchanged apart from parsing the dates.

## The analysis Borges starts from

`case.json` field `analysis`: the published analysis of the vote, as Steegen et al. reconstructed
it (the cell NMO1, F1, R1, ECL1, EC1 of their Study 2 grid). The cycle day comes from the last two
period dates, high fertility is days 7 to 14 and low fertility 17 to 25, single is relationship
answers 1 and 2 and committed 3 and 4, no other exclusion, and a logistic regression of the vote on
fertility, relationship status and their product. On these data that gives an interaction of
-1.6230, p .0038, n 303, the published b = -1.62, Wald(1) = 8.35, p = .004 with 131 + 172 women;
the cell percentages also match the paper (86.5 % and 73.7 % for Obama among single women, 40.4 %
and 23.4 % for Romney among women in relationships).

The text gives no hint of which changes matter. Borges is not told Steegen's grid.

## Steegen's grid on these data

`../../durante_study2/steegen_multiverse.py vote` ports their R code for this outcome: 210 valid
combinations of the next onset rule, the fertility window, the relationship coding, a cycle-length
exclusion and a certainty exclusion. 96 of 210 give p < .05. Of the ten single changes from the published cell,
two lose significance: keeping only women at least 6 of 9 sure of both period dates (p .1126,
n 204) and dating the next onset from the participant's own estimate (p .1135, n 279).

## Reproduce

```
uv run python evidence/held-out/durante_study2/prepare.py
uv run python evidence/held-out/durante_study2/steegen_multiverse.py vote
BORGES_CASES_DIR=evidence/held-out/cases uv run borges run --case fertility_vote --llm nebius
```
