# Hurricane names and deaths

Question: "Do hurricanes with more feminine names cause more deaths?"

A real dataset (94 Atlantic hurricanes that made landfall in the United States, 1950 to
2012) behind a well-known and contested finding. The case gives Borges a real analysis with a
published reference for how fragile the claim is across defensible analyses.

## Provenance and attribution

- Data: the hurricane table shipped with BLADE (Gu et al. 2024, "BLADE: Benchmarking Language
  Model Agents for Data-Driven Science"), data licensed ODC-By 1.0, code Apache-2.0. BLADE took
  it from Simonsohn, Simmons and Nelson (2020), who took it from the original paper.
- Original claim: Jung, Shavitt, Viswanathan and Hilbe (2014), "Female hurricanes are deadlier
  than male hurricanes", PNAS 111(24).
- Reference lane: Simonsohn, Simmons and Nelson (2020), "Specification curve analysis", Nature
  Human Behaviour 4, https://doi.org/10.1038/s41562-020-0912-z.
- `data.parquet` is built by `prepare.py` from a clone of the BLADE repository.

## Decision rule

The effect is the difference in predicted deaths between a hurricane with a feminine name and
one with a masculine name, other predictors at their sample means (Simonsohn et al.'s own
effect size, in additional deaths). The original claim is positive: an estimate above 0 with p
below 0.05 is `FEMININE NAMES DEADLIER`, anything else `NO CLEAR EVIDENCE`. The delta method
gives the interval and the p-value.

Column notes are neutral definitions of each column. They say nothing about outliers, which
storms matter or how robust the finding is.

## Reference lane (Simonsohn et al. 2020; page numbers are PDF pages of the 9-page offprint)

| Fact | Value | Where |
| --- | --- | --- |
| Reasonable specifications | 1,728 | p. 4 (Step 1); Fig. 2 caption, p. 3 |
| Significant in the predicted direction | 37 of 1,728 (2.1%) | p. 4; p. 6; Table 2, p. 6 |
| Median effect | 1.56 additional deaths (P = 0.536 against shuffled names) | Table 2, p. 6 |
| Range of point estimates | -1 to +12 additional deaths | p. 4 |
| Joint test on the share significant | P = 0.850 (425 of 500 shuffles reach 37) | Table 2 and text, p. 6 |
| Most estimates | "a very small minority ... is statistically significant" | p. 4 |

## Scripted lane

`fixtures/` is a hand-built plan labelled scripted: seven decisions taken from the menu of
Table 1 (p. 4) of the paper and the critiques it cites, none of them proposed by a model. It
replays offline at zero cost. The live recording, where Nemotron plans, codes and attacks the
analysis itself, is made separately and lives in `recorded-live/`.

`grid_summary.json` is the full grid of the scripted menu (1,944 specifications) for
comparison with the published curve: 59 significant (3.0%), median 1.25, range -2.1 to +10.3.
That is the same shape as the published curve (2.1%, median 1.56, range -1 to +12), computed
with this repository's estimator, not the authors' code.

## Scripted outcome

Default (original choices, re-estimated as a marginal effect): +4.1 additional deaths, 95% CI
-3.0 to 11.2, p = 0.257, `NO CLEAR EVIDENCE`. Three of the fourteen single-decision changes
reach `FEMININE NAMES DEADLIER`: keep every storm, drop only the deadliest storm, damage in
2013 dollars. The scripted adversary options do not flip it.

## Rebuild

```
uv run python cases/hurricanes/prepare.py <path to BLADE clone>
PYTHONPATH=src uv run python cases/hurricanes/build_fixtures.py
uv run borges record-demo --case hurricanes --llm scripted
```
