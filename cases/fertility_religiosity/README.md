# Fertility and religiosity: does the effect depend on relationship status?

A live-only case with a published answer that Borges is not told. It has no scripted fixtures,
and it only runs with `llm=nebius` and a `NEBIUS_API_KEY`. Nothing in this directory was
produced by a model.

## The question and the rule

- Question: does the difference in religiosity between women at high and at low fertility
  depend on relationship status, with women in committed relationships more religious at high
  fertility and single women less?
- Rule: the claim holds (FERTILITY SHIFTS RELIGIOSITY) if the fertility by relationship status
  interaction on mean religiosity is above 0 with p < 0.05. Otherwise there is no clear evidence.

## Data

- 275 women, Study 1 of Durante, K. M., Rae, A., & Griskevicius, V. (2013). The fluctuating
  female vote: Politics, religion, and the ovulatory cycle. Psychological Science, 24(6),
  1007-1016. https://doi.org/10.1177/0956797612466416
- Taken from the BLADE benchmark (Gu, K., et al. (2024). BLADE: Benchmarking Language Model
  Agents for Data-Driven Science. Findings of EMNLP 2024), file
  `blade_bench/datasets/fertility/data.csv` at commit `fc2e0fd`, released under the Open Data
  Commons Attribution License (ODC-By 1.0). Attribution is the two citations above. The only
  change is that the three date columns are stored as dates.
- Regenerate with `uv run --no-sync python cases/fertility_religiosity/prepare.py` (downloads
  the CSV into the git-ignored `data/raw/`).
- The column notes are BLADE's column descriptions, which quote the questionnaire. They do not
  mention any way of processing the data.

## What is known about the answer

The case was chosen because the answer is published and independent of Borges:

- Durante et al. (2013) classify women as high fertility (cycle days 7-14) or low (17-25), count
  cycle days back from a next onset computed from the last two period dates, treat response
  options 1-2 as single and 3-4 as committed, and exclude no one else. On these data that gives
  F(1, 159) = 6.46, p = .012, n = 163.
- Steegen, S., Tuerlinckx, F., Gelman, A., & Vanpaemel, W. (2016). Increasing transparency
  through a multiverse analysis. Perspectives on Psychological Science, 11(5), 702-712.
  https://doi.org/10.1177/1745691616658637. Their Table 1 lists five processing choices (the
  fertility window, the next-onset estimate, the relationship coding, exclusion by cycle length
  and by date certainty), 120 consistent combinations for Study 1, and p < .05 in 7 of them.
  Their conclusion: the effect "seems too sensitive to arbitrary choices and thus too fragile to
  be taken seriously".

`steegen_multiverse.py` recomputes both from `data.parquet` and reproduces them exactly
(F = 6.46, p = .012; 7 of 120). Borges sees only the question, the rule, the data and the
column notes, and none of this section.
