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
2. **Forks reality.** Every step runs in a sandbox. At each decision point Borges
   snapshots the exact execution state and branches one universe per alternative. Shared
   prefixes are computed once. On the ConTree backend each checkpoint is a VM-isolated
   sandbox image. The default local backend is a subprocess per step (scrubbed environment,
   AST code guard, per-step timeout) and is not VM isolation.
3. **Argues against you, with code.** An adversarial analyst inspects the real intermediate
   state and proposes new defensible choices aimed at reversing the conclusion. An
   independent judge scores how defensible each one is, and only defensible ones enter the
   garden.
4. **Finds the minimal flip.** Borges searches for the smallest set of defensible changes
   (one decision, then two, then three) that turns your decision around, and re-executes it from scratch
   to prove it reproduces.
5. **Lets you step into any universe.** Every universe shows its exact code, row counts,
   result, checkpoint ids and the chain of step scripts that reproduces it.

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
  checkpoints, selected with `BORGES_BACKEND=contree`. Implemented against `contree-sdk`
  and contract-tested; the only live check is a test that skips without credentials, and
  the hosted demo does not use it.
- **Nebius AI Cloud:** the Docker image is built to be deployed there. Nothing in this
  repository deploys it.
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
3. With `NEBIUS_API_KEY` set, the curated cases run **live on Nemotron via Token Factory**,
   under a hard spend cap, with the token and dollar cost shown. Live runs on a curated case
   use its own question and decision rule.
4. `make serve` opens the web app:
   - pick a case;
   - watch the garden grow live as sandboxes fork;
   - see the verdict card flip;
   - step into the flipping universe;
   - read the spec curve and the decision influence.
   Scripted demo runs replay offline, so the hosted demo never breaks and costs nothing. The
   hosted demo replays a scripted demo run (hand-built, not a live model run) and runs scripted on local subprocess sandboxes. Live
   Nemotron runs are on curated cases only, and stop when the spend cap is used up.
5. `make test` is green: Python unit and integration tests, ruff, the frontend type-check,
   tests and build, and an in-process end-to-end API test (a scripted run over HTTP, SSE
   events, the universe detail and the SPA fallback route).
6. `docker build` produces one image that serves API and UI. It defaults to the local
   backend and the scripted model.
7. The ConTree backend is implemented against `contree-sdk` and contract-tested. A live smoke
   test runs when sandbox credentials are present.

## Uploads

Uploading your own dataset is an API feature (`POST /api/uploads`, then `POST /api/runs`
with `upload_id`); the web app has no upload card. Uploaded datasets need live mode
(`llm=nebius` with `NEBIUS_API_KEY`), because there are no recorded responses for them. On
a public instance they should run only on isolated sandboxes (`BORGES_BACKEND=contree`),
and `BORGES_LIVE_TOKEN` should be set so that only callers who know the token can start
them. The local backend runs generated code on the server's own machine, so it accepts
uploads only when `BORGES_ALLOW_UNTRUSTED_LOCAL=true` (set by `make dev` and `make serve`,
meant for a private machine).
