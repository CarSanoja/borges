# Red cards and skin tone

Curated case for Borges built from the many-analysts study of Silberzahn et al. (2018), in which
29 research teams analysed the same dataset to answer: are soccer referees more likely to give
red cards to dark-skin-toned players?

## Data

- Dataset: "Crowdstorming a many analysts dataset", player-referee dyads from the first male
  divisions of England, Germany, France and Spain, 2012-2013 season (146,028 dyads).
  Source: https://osf.io/gvm2z/ (file https://osf.io/download/fv8c3/).
- Team results: "Crowdsourcing Effects in OR.csv" (https://osf.io/download/fa743/), the odds
  ratio and 95% interval reported by each of the 29 teams.
- License: CC0 1.0 Universal (public domain dedication), read from the OSF API
  (`/v2/nodes/gvm2z/`, `node_license`). Redistribution is permitted, so `data.parquet` is committed.
- Attribution (courtesy, not required by CC0): Silberzahn, R., Uhlmann, E. L., Martin, D. P.,
  et al. (2018). Many analysts, one data set: Making transparent how variations in analytic choices
  affect results. Advances in Methods and Practices in Psychological Science, 1(3), 337-356.
  https://doi.org/10.1177/2515245917747646

## Files

- `prepare.py` downloads the raw files into `data/raw/` (git-ignored) and writes `data.parquet`
  with 15 columns and compact dtypes.
- `option_code.py` holds the option code for every option of the plan.
- `build_fixtures.py` computes the numbers and writes `fixtures/` and `case.json`.
- `validation.py`, `summary.py`, `plan_text.py` support the fixture build and the tests.

Regenerate with `uv run --no-sync python cases/red_cards/prepare.py` then
`uv run --no-sync python cases/red_cards/build_fixtures.py`.
