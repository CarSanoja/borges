# Beauty and teaching evaluations

A live-only case with a published answer that Borges is not told. It has no scripted fixtures,
and it only runs with `llm=nebius` and a `NEBIUS_API_KEY`. Nothing in this directory was
produced by a model.

## The question and the rule

- Question: do instructors rated as better-looking receive higher course teaching evaluations?
- Rule: BEAUTY PREMIUM if the effect of the beauty rating on the course evaluation (1-5) is above
  0 with p < 0.05. Otherwise there is no clear evidence.

## Data

- 463 courses taught by 94 instructors at the University of Texas at Austin, 2000-2002.
  Hamermesh, D. S., & Parker, A. (2005). Beauty in the classroom: Instructors' pulchritude and
  putative pedagogical productivity. Economics of Education Review, 24(4), 369-376.
  https://doi.org/10.1016/j.econedurev.2004.07.013
- Taken from the BLADE benchmark (Gu, K., et al. (2024). BLADE: Benchmarking Language Model
  Agents for Data-Driven Science. Findings of EMNLP 2024), file
  `blade_bench/datasets/teachingratings/data.csv` at commit `9417ac5`, released under the Open
  Data Commons Attribution License (ODC-By 1.0). Attribution is the two citations above. The only
  change is that the row-number column is dropped.
- Regenerate with `uv run --no-sync python cases/teaching_ratings/prepare.py` (downloads the CSV
  into the git-ignored `data/raw/`).
- The column notes are BLADE's column descriptions, plus which column is the outcome and which
  the exposure.

## What is known about the answer

Hamermesh and Parker report a positive effect of beauty on evaluations that survives their
alternative specifications. On these data, with standard errors clustered by instructor (each
instructor teaches several courses):

| Specification | Beauty effect | 95% CI | p |
|---|---|---|---|
| Evaluation on beauty only | 0.133 | [0.025, 0.241] | 0.016 |
| OLS with gender, minority, native, tenure, division, credits | 0.165 | [0.069, 0.260] | 0.0008 |
| The same, weighted by the number of students evaluating | 0.275 | [0.160, 0.390] | 3e-6 |

The weighted model is the one usually quoted from the paper (0.275). The case is the robust
counterpart of `fertility_religiosity`: a sound tool should find no defensible flip here.

## What Borges found

The live recording (`recorded-live/`, 7 October 2026, run `r_20261007T013204_6521d3`) says BEAUTY
PREMIUM: 0.1645 [0.1034, 0.2257], p 1.3e-7, n 463, the second row of the table above, with no flip in
20 universes. Its farthest universe, with no covariates and errors clustered by instructor, is the
first row: 0.1330 [0.0252, 0.2408], p 0.016. All nine live runs of 6 and 7 October said BEAUTY
PREMIUM and none found a flip. The plan's weighted option weights each course by 1 / students,
the inverse of the third row's weighting by the number of students evaluating, so the paper's
weighted model was not in this multiverse; the judge accepted the inverse weights, and its six
universes gave 0.12 to 0.16. Refit and runs: `evidence/refit.md`, `evidence/repeats.md`.
