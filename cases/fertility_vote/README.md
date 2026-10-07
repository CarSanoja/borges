# Fertility and the vote: how fragile is the published analysis?

A live-only, held-out case. It was added on 7 October 2026 after the code it runs on was frozen,
and every run of it is reported in `evidence/held-out.md`, failures included. Borges was not
developed on these data: the fertility cases use Study 1 of the same paper; this is Study 2, a
different sample, a binary outcome and a logistic model. Nothing in this directory was produced by
a model except the recording.

## Data

Durante, Rae and Griskevicius (2013), *The fluctuating female vote*, Psychological Science 24(6),
Study 2: 502 women surveyed online before the 2012 US presidential election. Steegen, Tuerlinckx,
Gelman and Vanpaemel (2016) published the raw data on OSF (https://osf.io/zj68b/); their supplement
says the original author gave them permission to make the data publicly available. The OSF project
states no licence. `prepare.py` downloads the file, checks its SHA-256 and writes `data.parquet`
unchanged apart from parsing the dates.

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

`steegen_multiverse.py` ports their R code for this outcome: 210 valid combinations of the next
onset rule, the fertility window, the relationship coding, a cycle-length exclusion and a
certainty exclusion. 96 of 210 give p < .05. Of the ten single changes from the published cell,
two lose significance: keeping only women at least 6 of 9 sure of both period dates (p .1126,
n 204) and dating the next onset from the participant's own estimate (p .1135, n 279).

## Reproduce

```
uv run python cases/fertility_vote/prepare.py
uv run python cases/fertility_vote/steegen_multiverse.py
```
