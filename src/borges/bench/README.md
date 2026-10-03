# BLADE benchmark

An external, measured check of what Borges explores, using BLADE (Gu et al. 2024, "BLADE:
Benchmarking Language Model Agents for Data-Driven Science", code Apache-2.0, data ODC-By 1.0,
https://github.com/behavioral-data/BLADE). BLADE gives 12 datasets whose analysis decisions
(conceptual variables, data transforms, models) were annotated by experts. The question the
benchmark answers: of the decisions experts consider defensible, how many does Borges reach
(coverage), and how many of the analyses Borges runs are ones an expert would accept (hit rate)?
It compares two arms: `planner` (the adversary stage is switched off) and `adversary` (the full
pipeline).

## Run it

```
git clone https://github.com/behavioral-data/BLADE
uv run borges bench blade --datasets all --arms planner,adversary --llm nebius \
    --blade-dir <clone> --out evidence/blade/<date> --max-usd 2.0
uv run borges bench blade --llm scripted --datasets hurricane,teachingratings \
    --blade-dir <clone> --out /tmp/blade-scripted
```

Options: `--datasets <ids|all>`, `--arms planner,adversary`, `--llm scripted|nebius`,
`--repeats N` (independent runs per arm, each with a fresh response cache), `--matcher
llm|lexical`, `--matcher-model` (default the Token Factory Super model through the
OpenAI-compatible endpoint), `--max-rows` (datasets above it are sampled with a note; only
soccer, 146,028 rows, is), `--max-universes`, `--max-usd`. A live run refuses to start when
its estimated cost exceeds `--max-usd` and stops launching runs once the spend reaches it.

Output in `--out`: `summary.md` (table), `summary.json` (every number, run ids, commit, matcher,
cost), `submissions/<dataset>__<arm>.json` (every explored universe in BLADE's submission
format), `runs/` (events and meta of each run), `matcher-cache/`.

## What is written by hand: the decision rules

BLADE gives a research question, not a decision. `blade_rules.py` holds one explicit row per
dataset, written from each `info.json` research question: the testable question, the effect
(always on a signed scale where 0 means no effect), the hypothesised direction, alpha 0.05 and
the columns that stand for the independent and dependent variable. Where `info.json` asks an
open question ("which factors influence...") the row names the direction chosen and says so in
its `direction` field. These rows are our choice, not BLADE's, and the benchmark scores which
decisions are explored, not whether any verdict is right.

| dataset | hypothesised direction |
| --- | --- |
| affairs | children lower affairs |
| amtl | humans lose more teeth than non-human primates |
| boxes | reliance on the majority grows with age |
| caschools | a lower student-teacher ratio gives higher scores |
| crofoot | a larger relative group size raises the chance of winning |
| fish | live bait raises the catch per hour |
| hurricane | feminine names raise deaths |
| mortgage | women are denied more often |
| panda_nuts | older chimpanzees crack nuts more efficiently |
| reading | Reader View raises reading speed |
| soccer | darker skin tone raises red cards |
| teachingratings | beauty raises evaluations |

## How a universe becomes a BLADE analysis

Every distinct finished universe (distinct by the code of its chosen options) becomes one
`EntireAnalysis`: conceptual variables, a `transform(df)` function, and a `model(df)` function.
The conceptual variables are read off the executed code, not invented: the columns the code
references are classified as IV or DV by the rule's column lists (the IV is taken from the
feature and filter steps first, so a column used only to compute the effect does not count) and
every other referenced column is a control, described with the dataset's own column
description. Transform and model descriptions are the plan's own option labels and specs.

## Matching and metrics, and where they differ from BLADE

BLADE's own package pins pandas 1.5.3 and an LLM stack that cannot install next to Python 3.13,
so it is not imported. Instead this module reimplements the evaluation's metric definitions
and adapts its matching prompts (`blade_prompts.py`, attribution there; Apache-2.0).

- Conceptual variables: BLADE's prompt and scale; a pair counts as a match at similarity 8 or
  more, exactly as in BLADE's `calc_metrics`.
- Models: BLADE's prompt, any pair returned is a match; coverage is capped by the number of
  runs as in BLADE.
- Coverage is the share of expert decisions matched by any explored universe; hit rate is the
  mean over universes of the share of its decisions that match an expert decision; F1 is their
  harmonic mean. Reported for conceptual variables, models and transforms.
- Differences, stated openly: transforms are matched semantically by the matcher on the plan's
  option text, not by BLADE's hashing of the resulting data values; the model-with-variables
  and transform-graph metrics are not computed; a universe is one BLADE run. The scores are
  BLADE-style, not comparable with the leaderboard.
- The scripted mode uses a token-overlap matcher. It proves the plumbing end to end and its
  numbers are not scores. Only the hurricane and teachingratings datasets have scripted plans.
