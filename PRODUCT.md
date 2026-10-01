# Borges — product description

> **Every conclusion is one path through a garden of forking analyses.
> Borges walks the others, and shows you the one defensible choice that flips your decision.**

## The problem

Decisions are made on a single analysis of the data: ship the feature, publish the finding,
fund the program. But the same data, analysed by competent people making *defensible*
choices, routinely supports opposite conclusions.

- **2018, Silberzahn et al.** 29 research teams got the same dataset and the same question:
  are dark-skin-toned soccer players more likely to receive red cards? Their answers ranged
  from no effect (odds ratio 0.89) to nearly triple (2.93). 20 teams said yes, 9 said no.
  Nobody made a mistake. They made different reasonable choices.
- **2026, PNAS ("Many AI analysts, one dataset").** AI analysts reproduce the same spread.
  Steering an agent's persona moves support for a hypothesis by 34 to 66 points.
- Today, more and more analyses are written by AI agents. Each one returns a confident answer
  along a single path, and nobody shows you the paths it didn't take.

Statisticians call this the *garden of forking paths*, after Jorge Luis Borges' 1941 story
about a labyrinth in which every possible choice happens at once. Until now the garden was a
metaphor, because nobody could afford to walk it.

## What Borges does

You give Borges a dataset, a question and the decision rule you'll act on (for example
*"ship if the conversion lift is positive with p < 0.05"*).

1. **Plans the analysis like an expert.** Nemotron reads the data profile and writes the
   analysis as a sequence of steps. At every step where competent analysts disagree, it lists
   the defensible alternatives: exclusions, outcome definitions, covariates, models.
2. **Forks reality.** Every step runs in an isolated, VM-backed sandbox. At each decision
   point Borges snapshots the exact execution state and branches one universe per
   alternative. Shared prefixes are computed once.
3. **Argues against you, with code.** An adversarial analyst inspects the real intermediate
   state and proposes new defensible choices aimed at reversing the conclusion. An
   independent judge scores how defensible each one is, and only defensible ones enter the
   garden.
4. **Finds the minimal flip.** Borges searches for the smallest set of defensible changes
   (one decision, then two, then three) that turns your decision around, and re-executes it from scratch
   to prove it reproduces.
5. **Lets you step into any universe.** Every universe is a reproducible checkpoint chain with
   its exact code, row counts and result.

The output is a **fragility report**:
- the original verdict;
- the minimal defensible flip and its justification;
- which decisions move the result most, measured by intervening on that decision alone;
- the share of explored universes that agree with you;
- the full specification curve.

## Who it is for

- **Product and growth teams** shipping on A/B tests. First audience: the cost of a false
  "ship" is real and recurring.
- **Anyone acting on an AI analyst's answer.** Borges is the second opinion of a thousand
  analysts.
- **Researchers before submission, reviewers, data journalists.**

## Why it is new

Academic work in 2026 (PNAS; Miao, Pritchard and Zou; ForkSCOPE) samples *independent*
end-to-end AI analyses and maps their disagreement after the fact. ForkSCOPE states its own
limitation: attribution is observational, not interventional. Borges branches the
**execution state itself** at each decision. Sibling universes therefore differ in exactly
one choice, and the influence of each decision is measured by intervention, under a fixed
continuation protocol. Borges also turns the garden into an answer you can act on: the
minimal flip.

## Built on Nebius and NVIDIA

- **NVIDIA Nemotron 3 on Nebius Token Factory**, three models in five roles:
  - Super 120B plans, argues as the adversary and judges defensibility;
  - Nano 30B writes the code for every branch (cheap and massively parallel);
  - Ultra 550B, with 1M of context, reads the whole garden and writes the report.
- **Nebius Token Factory Sandboxes (ConTree):** VM-isolated execution with git-like
  checkpoints. Every universe is a branch, and every flip is replayable.
- **Nebius AI Cloud:** hosts the app.
- **Tavily (optional):** grounds an alternative's justification in methodological sources.

## Goal of the hackathon build (definition of done)

Borges is finished when all of these hold, on a clean clone:

1. `make demo-cli` runs the **checkout A/B case** end to end with deterministic recorded
   models and the local branch backend. It reports the original verdict **SHIP**, finds the
   planted single-decision flip (excluding internal test accounts) to **DON'T SHIP**, and
   verifies it reproduces.
2. The **red-cards case** (Silberzahn data) runs end to end. Its specification curve spans
   the range of the 29 human teams, and the report names the decisions that split
   "bias detected" from "no clear evidence".
3. With `NEBIUS_API_KEY` set, the same runs work **live on Nemotron via Token Factory**, under
   a hard spend cap, with the token and dollar cost shown.
4. `make serve` opens the web app:
   - pick a case;
   - watch the garden grow live as sandboxes fork;
   - see the verdict card flip;
   - step into the flipping universe;
   - read the spec curve and the decision influence.
   Recorded runs replay offline, so the hosted demo never breaks and costs nothing.
5. `make test` is green: Python unit and integration tests, ruff, the frontend type-check and
   build, and an end-to-end smoke test of the API serving the UI.
6. `docker build` produces one image that serves API and UI, ready for Nebius AI Cloud.
7. The ConTree backend is implemented against `contree-sdk` and contract-tested. A live smoke
   test runs when sandbox credentials are present.
