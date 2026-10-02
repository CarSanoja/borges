# Borges — product description

> **Every conclusion is one path through a garden of forking analyses.
> Borges walks the others, and shows you the one defensible choice that flips your decision.**

## The problem

Decisions are made on a single analysis of the data: ship the feature, publish the finding,
fund the program. But the same data, analysed by competent people making *defensible*
choices, routinely supports opposite conclusions.

- **2018, Silberzahn et al.** 29 research teams got the same dataset and the same question:
  are dark-skin-toned soccer players more likely to receive red cards? Their odds ratios
  ranged from 0.89 to 2.93 (median 1.31). 20 teams found a significant effect, 9 did not.
  Nobody made a mistake. They made different reasonable choices.
- **2026, PNAS ("Many AI analysts, one dataset", Bertran, Fogliato and Wu).** About 5,000
  autonomous AI analysts on three datasets reproduce the same spread. Support for the
  hypothesis differs by 34 to 66 percentage points between skeptical and confirmation-seeking
  personas, depending on the dataset.
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
   AST code guard as a lint, per-step timeout) and is not isolation: live and upload runs on a
   shared server need the VM backend.
3. **Argues against you, with code.** An adversarial analyst inspects the real intermediate
   state and proposes new defensible choices aimed at reversing the conclusion. An
   independent judge scores how defensible each one is, and only defensible ones enter the
   garden.
4. **Finds the minimal flip.** Borges searches for the smallest set of defensible changes
   (one decision, then two, then three) that turns your decision around, and re-executes it from scratch
   to prove it reproduces.
5. **Lets you step into any universe.** Every universe shows its exact code, row counts,
   result, checkpoint ids, and a command you can paste to reproduce it
   (`borges reproduce --case <id> --universe <id>` for the recorded demos, or a downloadable
   script that runs on your own copy of the data).

The output is a **fragility report**:
- the original verdict;
- the minimal defensible flip and its justification;
- which decisions move the result most, measured by intervening on that decision alone;
- the share of explored universes that agree with you, and the range of the effect across them;
- the full specification curve, with the human teams' results as a reference lane where a
  case has them.

The flip is presented as the nearest crossing Borges found, not as a typical analysis: the
search favours flips, and a p-value crossing can leave the effect positive (red cards: odds
ratio 1.34 to 1.20, p 0.0006 to 0.055).

## Who it is for

- **Product and growth teams** shipping on A/B tests. First audience: the cost of a false
  "ship" is real and recurring.
- **Anyone acting on an AI analyst's answer.** Borges is the second opinion of a thousand
  analysts.
- **Researchers before submission, reviewers, data journalists.**

## Related work

What exists, verified against the primary sources (September and October 2026):

| Work | What it does | Source |
|---|---|---|
| Specification curve analysis (Simonsohn, Simmons, Nelson 2020) and multiverse analysis (Steegen et al. 2016) | Run all defensible combinations of analytic choices and show the distribution of results. The idea Borges builds on | [Nature Human Behaviour](https://doi.org/10.1038/s41562-020-0912-z) |
| `specr` (Masur and Scharkow) | R package to set up, run and plot a specification curve, with inference on the curve in recent versions. The analyst declares outcomes, predictors, models, controls and subsets in `setup()`; it proposes nothing | [CRAN](https://cran.r-project.org/package=specr), [site](https://masurp.github.io/specr/) |
| Boba (Liu, Kale, Althoff, Heer; IEEE TVCG 2021) | A DSL in which the analyst writes shared code once plus local variations; the compiler emits one script per path, and a visualizer links results to the decision space to find consequential decisions | [paper](https://arxiv.org/pdf/2007.05551), [project](https://idl.uw.edu/papers/boba) |
| `multiverse` R package (Sarma, Kale, Moon, Taback, Chevalier, Hullman, Kay) | Declare alternatives with `branch()` inside an R notebook; builds the multiverse from local changes to one analysis, runs paths in parallel and isolates failures. Alternatives are never proposed automatically | [CRAN](https://cran.r-project.org/package=multiverse), [docs](https://mucollective.github.io/multiverse/) |
| ForkSCOPE (Balaji, Yeltekin, Zheng, arXiv 2609.12438, Sept 2026) | Human-AI pipeline that induces the forks and a taxonomy bottom-up from the code of many end-to-end analyses and shows them in an evidence-linked viewer. Its fork-to-outcome attribution is observational: choices co-occur and were not assigned | [arXiv](https://arxiv.org/abs/2609.12438) |
| "The Agentic Garden of Forking Paths" (Miao, Pritchard, Zou, arXiv 2607.01507, July 2026) | AI agents with different personas reproduce 72% of a human ideological gap on 42 teams' immigration analyses; introduces the m-value and an Agentic Bootstrap to place a reported finding in the space of plausible analyses | [arXiv](https://arxiv.org/abs/2607.01507) |
| "Many AI analysts, one dataset" (Bertran, Fogliato, Wu; PNAS 2026) | About 5,000 autonomous analyst runs over 3 datasets, 4 LLMs and 5 personas; verdicts and effect sizes reverse between runs and persona steering shifts the distribution | [PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC13393493/) |

**What Borges does that these do not.**
1. **An adversary that proposes forks on the live intermediate state.** Boba, `multiverse`
   and `specr` need the analyst to list every alternative up front. The AI-analyst studies
   and ForkSCOPE sample whole independent analyses and read the forks off afterwards.
   Borges's adversary reads the real row counts and estimates at a step, argues against the
   conclusion with code, and an independent judge scores how defensible each proposal is
   before it enters the garden. This is designed and tested with scripted models; whether
   Nemotron proposes good forks is the first thing the live run must show.
2. **The minimal defensible flip.** It searches one change, then two, then three, and
   re-executes the winner from scratch, so the output is the smallest decision that turns
   yours around, not only a distribution.
3. **Influence by intervention on a shared-prefix checkpointed execution.** Sibling
   universes differ in exactly one choice from the same checkpoint, so the influence of a
   decision is an interventional contrast under a fixed continuation protocol, where
   ForkSCOPE's attribution is observational.

**What it does not do better.**
- `multiverse` also avoids recomputing shared work, and Boba and `multiverse` are mature,
  peer-reviewed tools with visual analysis and (Boba) sensitivity tooling. Borges's prefix
  sharing is not novel in itself; sharing the real execution state across processes is.
- `specr` offers inference on the whole curve; Borges reports a robustness share over the
  universes it explored and does not test the curve.
- Miao et al.'s m-value and the PNAS study sample the analysis space statistically; Borges
  searches it adversarially and says so, so its flip is biased toward finding one.
- Borges explores the options its planner and adversary propose, under one estimand. Human
  teams also change the estimand and the model family, so Borges's curve is narrower than the
  teams' (red cards: 1.20 to 1.36 against 0.89 to 2.93).
- Mature tools are used and checked by researchers today; Borges has not run a live model
  and has no external users yet.

## Built on Nebius and NVIDIA

- **NVIDIA Nemotron 3 on Nebius Token Factory**, three models in five roles:
  - Super 120B plans, argues as the adversary and judges defensibility;
  - Nano 30B writes the code for every branch (cheap and massively parallel);
  - Ultra 550B, with 1M of context, reads the whole garden and writes the report.
- **Nebius Token Factory Sandboxes (ConTree):** VM-isolated execution with git-like
  checkpoints, selected with `BORGES_BACKEND=contree`. Implemented against `contree-sdk`
  and contract-tested with a fake SDK; the only live check is a test that skips without
  credentials, and it has never run against the real service.
- **Nebius AI Cloud:** the Docker image is built to be deployed there. Nothing in this
  repository deploys it, and there is no public hosted demo yet.
- **Status:** no Nemotron call has run yet (no key on the development machine). The demos
  replay hand-built scripted fixtures, labelled as such. `make live-smoke` and
  `make record-live` are the first live steps.
- **Tavily (optional):** grounds an alternative's justification in methodological sources.

## Goal of the hackathon build (definition of done)

Borges is finished when all of these hold, on a clean clone:

1. `make demo-cli` runs the **checkout A/B case** end to end with deterministic recorded
   models and the local branch backend. It reports the original verdict **SHIP**, finds the
   planted single-decision flip (excluding internal test accounts) to **DON'T SHIP**, and
   verifies it reproduces. The data is synthetic and the flip is planted.
2. The **red-cards case** (Silberzahn data, real) runs end to end. Its specification curve
   (odds ratio 1.20 to 1.36 over 30 universes) is narrower than the range of the 29 human teams
   (0.89 to 2.93), which is shown next to it; the report names the decisions that split
   "bias detected" from "no clear evidence". The two MARP cases (real, CC-BY 4.0) run the same
   way against 110 and 105 teams.
3. With `NEBIUS_API_KEY` set, the curated cases run **live on Nemotron via Token Factory**,
   under a hard spend cap, with the token and dollar cost shown. Live runs on a curated case
   use its own question and decision rule.
4. `make serve` opens the web app:
   - pick a case;
   - watch the garden grow live as sandboxes fork;
   - see the verdict card flip;
   - step into the flipping universe;
   - read the spec curve and the decision influence.
   Scripted demo runs replay offline and cost nothing; they are hand-built, not live model
   runs, and are labelled as scripted replays. Live Nemotron runs stop when the spend cap is
   used up. Not yet met: no live run has happened and there is no hosted demo.
5. `make test` is green: Python unit and integration tests, ruff, the frontend type-check,
   tests and build, and an in-process end-to-end API test (a scripted run over HTTP, SSE
   events, the universe detail and the SPA fallback route).
6. `docker build` produces one image that serves API and UI. It defaults to the local
   backend and the scripted model.
7. The ConTree backend is implemented against `contree-sdk` and contract-tested. A live smoke
   test runs when sandbox credentials are present.

## Uploads

Uploading your own dataset (CSV or parquet) works from the landing page card and over the API
(`POST /api/uploads`, then `POST /api/runs` with `upload_id`). The card is enabled only when
`/api/health` reports `uploads_available`, and otherwise states why. Uploaded datasets need live mode
(`llm=nebius` with `NEBIUS_API_KEY`), because there are no recorded responses for them. On
a public instance they should run only on isolated sandboxes (`BORGES_BACKEND=contree`),
and `BORGES_LIVE_TOKEN` should be set so that only callers who know the token can start
them. The local backend runs generated code on the server's own machine, so it accepts
uploads only when `BORGES_ALLOW_UNTRUSTED_LOCAL=true` (set by `make dev` and `make serve`,
meant for a private machine).
