# Borges — product description

> **How fragile or robust is this decision, and which analytic choice matters?
> Borges re-runs the analysis along other defensible paths, reports how many agree with
> yours, and shows the smallest flip it found.**

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
about a labyrinth in which every possible choice happens at once. Multiverse and
specification-curve tools already walk part of the garden when an analyst lists the paths;
Borges tries to make that cheap enough to do on every analysis, and to propose paths nobody listed.

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
   AST code guard as a first-layer lint, a runtime audit-hook policy that blocks process creation,
   network and writes outside the step directory and allowlists reads, denying `.env`,
   `/proc/*/environ` and the user's home, per-step timeout) and is not isolation: live and upload runs on a
   shared server need the VM backend.
3. **Argues against you, with code.** An adversarial analyst inspects the real intermediate
   state and proposes new defensible choices aimed at reversing the conclusion. An
   independent judge scores how defensible each one is, and only defensible ones enter the
   garden.
4. **Finds the smallest flip a bounded search can find.** Borges searches one decision, then
   two, then three, trying at most 10 combinations per level (a capped beam search, ordered by
   how close each got to the threshold), so the result is the smallest flip found, not a
   proven minimum. It re-executes the winner from scratch to prove it reproduces. The search
   budget is reported with the verdict.
5. **Lets you step into any universe.** Every universe shows its exact code, row counts,
   result, checkpoint ids, and a command you can paste to reproduce it
   (`uv run borges reproduce --case <id> --universe <id>` after `uv sync`, for the recorded demos, or a downloadable
   script that runs on your own copy of the data).

The output is a **fragility report**:
- the original verdict;
- the smallest defensible flip found by the bounded search, and its justification;
- which decisions move the result most, measured by intervening on that decision alone;
- the share of explored universes that agree with you, and the range of the effect across them;
- the full specification curve, with the human teams' results as a reference lane where a
  case has them.

The flip is presented as the nearest crossing Borges found, not as a typical analysis: the
search favours flips, and a p-value crossing can leave the effect positive (red cards: odds
ratio 1.34 to 1.20, p 0.0006 to 0.055).

### How much to trust a flip: the calibration result

`evidence/calibration.md` (offline, scripted, nothing live): 504 synthetic checkout datasets of
about 30,000 sessions through the real pipeline with a fixed menu (5 steps x 2 options plus
one scripted adversary option), seeds `20261002 + cell_index * 1,000,000 + i`, Wilson 95%
intervals. Headline cells have 80 datasets; the secondary cells (24 or 40) have intervals up
to about 20 points.

- Large true effect (0.010 lift, about 99% power), no artefact: a flip was reported in
  13/80 = 16% (95% interval 10 to 26%), all significance crossings with the same sign; direction
  flips 0/80 (upper bound 5%).
- Null effect where the default analysis wrongly says SHIP (80 of 3,164 scanned datasets,
  2.5%, the nominal rate): flip reported in 71/80 = 89% (80 to 94%), all significance
  crossings, 0/80 direction flips.
- Null effect with the planted artefact: flip reported in 78/80 = 98% (91 to 99%); through the
  internal-traffic exclusion 76/80 = 95% (88 to 98%); direction flips 35/80 = 44% (33 to 55%).
  At 80% power with the artefact: via internal traffic 55/80 = 69% (58 to 78%), 0 direction
  flips; at a large effect with the artefact 5/24 = 21% (9 to 40%, small cell).
- Direction flips on clean data: 0 of 272 datasets (upper 95% bound about 1.4%).

The uncomfortable conclusion: the bounded search is biased toward flips of the significance
kind. On clean data with a large true effect it reports a significance-only flip 16% of the
time and never a direction flip in 272 clean datasets, so a flip label must say which kind it
is. A significance flip (same sign, p crosses 0.05, like red cards OR 1.34 to 1.20) is weak
evidence on its own; a sign-reversing flip is specific. Detection of the artefact falls as
the true effect grows, so no flip does not prove no artefact. The rates apply to this fixed
menu, not to arbitrary datasets, and the default analysis ignores clustering by user.

**Verdict wording.** The docs and the verdict card lead with the robustness share ("N of M
paths agree"), then the smallest flip found and its kind (direction or significance).

## Who it is for

- **Anyone acting on an AI analyst's answer.** Borges is a second opinion that shows how many
  other defensible analyses agree.
- **Researchers before submission, reviewers, data journalists**: the cases that work end to
  end today are many-analysts studies with real data and published team results.
- **Product and growth teams shipping on A/B tests** are a plausible next audience, not a
  validated one. The only business-style cases are a synthetic checkout test (planted effect)
  and a live-only real bank-telemarketing case (`bank_marketing_calls`, CC BY 4.0) that no one
  has run yet. There is no business user or pilot behind this claim.

## Related work

What exists, verified against the primary sources (September and October 2026):

| Work | What it does | Source |
|---|---|---|
| Specification curve analysis (Simonsohn, Simmons, Nelson 2020) and multiverse analysis (Steegen et al. 2016) | Run all defensible combinations of analytic choices and show the distribution of results. The idea Borges builds on | [Nature Human Behaviour](https://doi.org/10.1038/s41562-020-0912-z) |
| `specr` (Masur and Scharkow) | R package to set up, run and plot a specification curve, with inference on the curve in the development version 1.0.1 (May 2024). The analyst declares outcomes, predictors, models, controls and subsets in `setup()`; it proposes nothing | [CRAN](https://cran.r-project.org/package=specr), [site](https://masurp.github.io/specr/) |
| RobustiPy (Valdenegro, Yan, Dai, Rahal; arXiv 2506.19958, June 2025; GPL-3.0) | Python library for multiverse and specification-curve analysis at scale: combinatorial specification search, bootstrap inference, model selection and averaging, joint inference, out-of-sample validation and explainable-AI attribution of covariates; benchmarked on about 672 million simulated regressions. Verified from the arXiv abstract and the project page; we did not run it or read its full source. Contrast: it enumerates specifications efficiently, whereas Borges has an adversary propose new forks mid-analysis on forked, checkpointed execution, searches for the smallest flip and reproduces it; RobustiPy is stronger on statistical inference over the curve and scale | [arXiv](https://arxiv.org/abs/2506.19958), [code](https://github.com/RobustiPy/robustipy), [docs](https://robustipy.readthedocs.io/) |
| Boba (Liu, Kale, Althoff, Heer; IEEE TVCG, VAST 2020) | A DSL in which the analyst writes shared code once plus local variations; the compiler emits one script per path, and a visualizer links results to the decision space to find consequential decisions | [paper](https://arxiv.org/pdf/2007.05551), [project](https://idl.uw.edu/papers/boba) |
| `multiverse` R package (Sarma, Kale, Moon, Taback, Chevalier, Hullman, Kay) | Declare alternatives with `branch()` inside an R notebook; builds the multiverse from local changes to one analysis, runs paths in parallel and isolates failures. Alternatives are never proposed automatically | [CRAN](https://cran.r-project.org/package=multiverse), [docs](https://mucollective.github.io/multiverse/) |
| ForkSCOPE (Balaji, Yeltekin, Zheng, arXiv 2609.12438, Sept 2026) | Human-AI pipeline that induces the forks and a taxonomy bottom-up from the code of many end-to-end analyses and shows them in an evidence-linked viewer. Its fork-to-outcome attribution is observational: choices co-occur and were not assigned | [arXiv](https://arxiv.org/abs/2609.12438) |
| "The Agentic Garden of Forking Paths" (Miao, Pritchard, Zou, arXiv 2607.01507, July 2026; a different paper from the one above) | AI agents with different personas reproduce 72% of a human ideological gap on 42 teams' immigration analyses; introduces the m-value and an Agentic Bootstrap to place a reported finding in the space of plausible analyses. We found no public code for it | [arXiv](https://arxiv.org/abs/2607.01507) |
| "Many AI analysts, one dataset" (Bertran, Fogliato, Wu; arXiv 2602.18710, Feb 2026; PNAS 2026) and its open-source code, [amazon-science/agentic-forking-path](https://github.com/amazon-science/agentic-forking-path) (Apache-2.0) | The closest open implementation. Autonomous data-scientist agents (Inspect AI, Docker containers) each analyse the same dataset and hypothesis under a different persona prompt (neutral, skeptical, confirmation-seeking) over several independent epochs and models. A separate judge audits each run; a 3-pass LLM extraction then reads the analytic decisions off the finished runs, builds a taxonomy, and reports hypothesis-support rates per persona, p-value distributions, specification curves and a "compliance gap" as a p-hacking diagnostic. About 5,000 analyst runs over 3 datasets, 4 LLMs and 5 personas; verdicts and effect sizes reverse between runs and persona steering shifts the distribution | [arXiv](https://arxiv.org/abs/2602.18710), [PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC13393493/), [code](https://github.com/amazon-science/agentic-forking-path) |
| Fixed full grid over Borges's seeded options (our own baseline, `scripts/compare_grid.py`) | The `specr` or hand-written multiverse approach: the full Cartesian product of each curated case's seeded plan options, every universe executed through the same harness and local backend, with no adversary. Complete grids of 72, 32, 768 and 1,536 universes ran offline in 27, 12, 204 and 424 s. It finds the same smallest flip as Borges in every case (or none in either), at 2.4 to 102 times the universes. Not a run of `specr` itself or of `agentic-forking-path` | [evidence/grid_vs_search.md](evidence/grid_vs_search.md), [json](evidence/grid_vs_search.json) |

**What Borges does that these do not.**
1. **An adversary that proposes forks on the live intermediate state.** Boba, `multiverse`
   and `specr` need the analyst to list every alternative up front. `agentic-forking-path`,
   the PNAS study and ForkSCOPE sample whole independent analyses and read the forks off
   afterwards: a fork exists only if some agent happened to take it, and nothing is re-run
   from a shared state.
   Borges's adversary reads the real row counts and estimates at a step, argues against the
   conclusion with code, and an independent judge scores how defensible each proposal is
   before it enters the garden. This is designed and tested with scripted models; whether
   Nemotron proposes good forks is the first thing the live run must show.
2. **The smallest defensible flip found.** It searches one change, then two, then three
   (at most 10 combinations per level) and re-executes the winner from scratch, so the output
   is a specific decision that turns yours around, not only a distribution. It is the
   result of a capped search, not a proof of minimality.
3. **Influence by intervention on a shared-prefix checkpointed execution.** Sibling
   universes differ in exactly one choice from the same checkpoint, so the influence of a
   decision is an interventional contrast under a fixed continuation protocol, where
   ForkSCOPE's attribution is observational.

**Against `agentic-forking-path`, precisely.** It answers "how do autonomous analysts with
different incentives diverge?": its forks are whole independent analyses by personas, found
by sampling, and its decisions are extracted from the finished reports by an LLM. Borges
answers "how fragile is this one analysis, and which choice matters?": forks are explicit
options in a plan, executed from shared checkpoints, an adversary proposes new ones against
the conclusion, and each universe can be re-executed with `borges reproduce`. They are
similar in the goal (show the spread of defensible conclusions), in using LLM agents, and in
sandboxed execution. Borges is weaker on evidence: that code and paper were run live on about
5,000 real model runs and a published study, while Borges has never called a model. We have
not run their pipeline: it needs a live LLM API, which this machine does not have. The
measurable part, a fixed full grid over the same seeded options, was run offline (see
"What a statistician would object to" and `evidence/grid_vs_search.md`); a head-to-head
against their agents on the same dataset still does not exist.

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
- Persona sampling covers choices an LLM analyst would make unprompted, including ones that
  no planner listed; Borges's coverage is limited by its planner and adversary.
- Mature tools are used and checked by researchers today; Borges has not run a live model
  and has no external users yet.

## What a statistician would object to

Written as a skeptical reviewer would put it, each with Borges's honest answer. None of this
has been run live on a model.

1. **"Your option space is seeded by hand or by a model. It is not exhaustive, so 'robust'
   means robust to what you listed."** Correct. The curated cases are seeded from published
   many-analysts choices, and in live mode a planner and an adversary propose the rest; any
   fork nobody proposed is invisible, and a human team also changes the estimand and the
   model family (red cards: the teams span 0.89 to 2.93, Borges's curve 1.20 to 1.36). The
   robustness share is a statement about the explored menu, not about all defensible
   analyses. The measurable part: on the four cases the fixed full grid over the seeded
   options finds the same smallest flip as Borges, so the bounded search loses nothing
   inside the menu; it says nothing about the space outside it. Evidence:
   `evidence/grid_vs_search.md`.
2. **"Your adversary is biased toward flips by design."** Yes: it is told to argue against
   the conclusion, the search keeps the smallest flip it finds, and the beam ranks
   candidates by how far they move the estimate. The calibration measured the bias: with no
   real artefact and a false SHIP, a flip was reported 89% of the time, all of them
   significance crossings. For the same reason its robustness share is not a uniform
   sample: checkout 86% against the grid's 50%, red cards 87% against 90%, marp_norms 93%
   against 89.5%. Read a reported flip by its kind. Evidence: `evidence/calibration.md`,
   `evidence/grid_vs_search.md`.
3. **"Most flips are 'p crossed 0.05', which is noise near a threshold."** Agreed, and the
   flagship red-cards flip is of that kind (OR 1.34 to 1.20, still above 1). In the
   calibration, 0 of 272 clean datasets gave a direction flip, against 44% when an
   artefact is planted; significance flips are expected from noise even for a large real
   effect (16%). The report labels each flip `direction` or `significance`, and only the
   first is a strong claim. Evidence: `evidence/calibration.md`; the same pattern in the
   grid (marp_norms: the smallest flip is a significance crossing, 161 of 1,536 universes
   flip).
4. **"The LLM judge of defensibility has no ground truth."** True. Its scores gate which
   adversary proposals enter the garden, but there is no inter-rater check against human
   methodologists and no agreement statistic; in scripted mode the scores are fixtures, and
   no model has judged anything. The seeded options of the curated cases do not depend on
   the judge. Until a rater study exists, treat 'defensible' as a documented filter, not a
   validated measurement. No evidence file yet; this limit is open.
5. **"Forking paths inflate false discoveries, and you report a flip, not a corrected
   p-value."** Right. Borges does not adjust inference across the universes, does not test
   the specification curve (`specr` does, in its development version), and 'N of M agree'
   is a count over what was run, not a probability that the finding is true. It tells you
   which decision turns your verdict and how large the explored disagreement is; the
   decision rule is applied to each universe's own p-value. Evidence: the robustness shares
   in `evidence/grid_vs_search.md` (unweighted over the product, so a five-change universe
   counts as much as a single change).
6. **"Where is the head-to-head with a fixed grid or with agentic-forking-path?"** The
   fixed grid, offline, complete, on the four curated cases (72, 32, 768 and 1,536
   universes): same smallest flip in all four, 2.4 to 102 times fewer universes for Borges,
   and wall time only worth saving on the large spaces (marp_norms 19 s against 424 s; on
   red cards and checkout the grid took 27 and 12 s against 23 and 13 s). The grid finds
   nothing that Borges missed. What it does not test: Borges's adversary-proposed options
   (outside the grid), a live model, or any cost in tokens. `agentic-forking-path` needs a
   live LLM API and was not run, and neither were `specr` or RobustiPy, so there is no
   comparison of forks, flips and cost against them. Evidence: `evidence/grid_vs_search.md`.

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
   way against 110 and 105 teams. A live-only real business case, `bank_marketing_calls` (UCI Bank Marketing,
   CC BY 4.0), has no scripted fixtures or recording and runs only with `llm=nebius`.
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
them. The local backend runs generated code on the server's own machine (reads are allowlisted, and
`.env`, `/proc/*/environ` and the user's home are denied, but it is not isolation), so it accepts
uploads (refused otherwise, 400) only when `BORGES_ALLOW_UNTRUSTED_LOCAL=true` (set only by `make dev`,
meant for a private machine).
