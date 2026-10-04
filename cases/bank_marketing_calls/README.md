# Bank telemarketing: cap the calls?

A live-only case: it has no scripted fixtures and no scripted recording, and it only runs with
`llm=nebius` and a `NEBIUS_API_KEY`. Its recording, `recorded-live/events.jsonl`, was made
live on Nemotron on 4 October 2026 (32 calls, $0.0233; see `evidence/live-runs.md`). Nothing
else in this directory was produced by a model.

## The question and the rule

- Question: does each additional contact call to the same customer in a campaign reduce the
  chance that the customer subscribes to a term deposit?
- Rule: act (cap the calls per customer) if the odds ratio per additional call is below 1 with
  p < 0.05. Otherwise there is no case for a cap.

## Data

- Dataset: "Bank Marketing", 45,211 rows, 16 input columns plus `y` (subscribed), direct
  marketing phone campaigns of a Portuguese bank. Moro, S., Rita, P., & Cortez, P. (2014).
  UCI Machine Learning Repository. https://doi.org/10.24432/C5K306
  (page: https://archive.ics.uci.edu/dataset/222/bank+marketing).
- License: Creative Commons Attribution 4.0 International (CC BY 4.0), as stated on the UCI
  page of the dataset (the primary source). It allows sharing and adaptation for any purpose
  with credit, so `data.parquet` is committed. Attribution is the citation above. The only
  change is that `y` is stored as 0/1; all 17 columns are kept.
- Related paper: Moro, S., Cortez, P., & Rita, P. (2014). A data-driven approach to predict the
  success of bank telemarketing. Decision Support Systems.
  https://doi.org/10.1016/j.dss.2014.03.001

Regenerate with `uv run --no-sync python cases/bank_marketing_calls/prepare.py` (downloads
the CSV into the git-ignored `data/raw/`).

## What is known about the answer

The data are observational: the number of calls is not assigned, so a lower subscription rate
at high call counts can come from who is hard to reach, not from the calls. There is no
published verdict on this question to compare against and there is no reference lane.

Before writing this case the author fitted nine plain logistic regressions on the data (raw;
adding customer covariates, month, channel and previous outcome; adding call duration; capping
at 10 calls; restricting to never-contacted customers). Every one gave an odds ratio per extra
call between 0.86 and 0.93 with p < 0.001. So the expected outcome is a robust "cap the calls"
verdict, and what a live run adds is whether any defensible fork flips it. That is a
pre-run expectation, not a Borges result; no Borges run exists for this case.

## Caveats

- `duration` (length of the last call) is only known after the call, so it is a post-treatment
  variable for the question; whether to adjust for it is itself a contested choice.
- `pdays = -1` means never contacted before; `contact`, `education`, `job` and `poutcome`
  have missing values.
- The column named `day_of_week` holds the day of the month in this file.
