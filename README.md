# Borges

**How fragile or robust is this decision, and which analytic choice matters? Borges re-runs
the analysis along other defensible paths, tells you how many agree with yours, and shows the
smallest flip it found.**

In three lines:

1. You give it a dataset, a question and the rule you will act on ("ship if the lift is
   positive with p < 0.05").
2. Nemotron plans the analysis, every choice forks a real sandbox, and an adversary proposes
   paths against your conclusion.
3. You get the share of universes that agree, the decisions that move the result, the
   smallest flip found by a bounded search, and a command that reproduces it.

Quickstart, offline, no key, from a fresh clone (Python 3.13 and [uv](https://docs.astral.sh/uv/)):

```bash
uv sync
uv run borges run --case marp_religiosity --llm scripted
uv run borges reproduce --case red_cards --universe u_a64c6b99f5
```

The first runs a real-data case with scripted models in about 18 s; the second re-executes one
recorded universe and prints `MATCH`. The status table below says what is and is not live.

Built for the [Nebius x NVIDIA Global AI Hackathon](https://nebiusglobalaihackathon.devpost.com/)
on **NVIDIA Nemotron 3** served by **Nebius Token Factory**. Every analysis step runs as a
branch of a sandbox: a local subprocess backend by default (no VM isolation), or Nebius
Token Factory Sandboxes (ConTree, VM-isolated) with `BORGES_BACKEND=contree`.

## Status: what has and has not run

Be clear about this before reading further.

| | State today |
|---|---|
| Nemotron through Token Factory | **Code paths written and tested against fakes. Nothing has run live yet**: there has been no `NEBIUS_API_KEY` on the development machine. `make live-smoke` and `make record-live` are the first live steps |
| ConTree sandboxes | Implemented against `contree-sdk` and contract-tested with a fake SDK. The live test is skipped without credentials. Never run against the real service |
| What the demos replay | **Scripted fixtures, hand-built, not model output.** They carry the model label `scripted` (or `scripted-fixture`), 0 tokens and $0. The CLI says so: `LLM calls: 16 scripted`, `cost: $0.0000 (scripted replay, no model called)` |
| What is real | The data, the option code, the sandbox execution and every statistic: each universe is really executed and re-executed by `borges reproduce` |
| Hosted public demo | None yet |

The recorded events (`cases/*/recorded/events.jsonl`) still list the configured role model
ids in the `run.started` `models` field, even though no model was called; the `llm` field of
the same event says `scripted`.

---

## The problem

In 2018, 29 research teams were given the same dataset and the same question: are soccer
referees more likely to give red cards to dark-skin-toned players? Their odds ratios ranged
from 0.89 to 2.93, and 20 teams found a significant effect while 9 did not. Nobody made a
mistake: they made different, defensible analysis choices
([Silberzahn et al., 2018](https://journals.sagepub.com/doi/10.1177/2515245917747646)).

AI analysts behave the same way
([Many AI analysts, one dataset, PNAS 2026](https://pmc.ncbi.nlm.nih.gov/articles/PMC13393493/)),
and more and more decisions rest on an analysis an AI wrote along a single path. It
returns one confident answer and never shows the paths it did not take.

## What Borges does

Give Borges a dataset, a question and the rule you will act on, for example *"ship if the
conversion lift is positive with p < 0.05"*.

1. **Nemotron plans the analysis like a senior statistician.** At every step where experts
   disagree it lists the defensible alternatives, and the conventional choice is the
   default.
2. **Every choice forks a real sandbox.** Each step runs in a sandbox (a subprocess on the
   local backend, a VM on ConTree). Each alternative branches from the exact filesystem
   state of the step before, and universes that share a prefix share its checkpoints.
3. **An adversarial analyst argues against your conclusion, with code.** It reads what the
   real data did at each step (row counts, the estimate) and proposes new options; an
   independent judge scores how defensible each one is, and only defensible ones enter the
   garden.
4. **Borges looks for the smallest defensible flip.** It tries one change, then two, then
   three (at most 10 combinations per level, those that moved the result closest to the
   threshold first), so the answer is the smallest flip a bounded search found, not a proven
   minimum. It re-executes the winning universe from a fresh sandbox to prove it reproduces.
5. **You can step into any universe** and see its exact code, row counts, checkpoint ids
   and result.

## The demo cases

| | Checkout A/B test (synthetic, effect planted) | Red cards (real data, 146,028 dyads) |
|---|---|---|
| Question | Does the new checkout increase conversion? | Do referees give dark-skinned players more red cards? |
| Default analysis | **SHIP**: +0.53 pp, 95% CI [0.14, 0.92], p = 0.008 | **BIAS DETECTED**: OR 1.34, 95% CI [1.13, 1.58], p = 0.0006 |
| Smallest flip found | 1 change: exclude internal test accounts | 3 changes together: the second rater only, referees with 22+ dyads, full covariates |
| Flipped result | **DON'T SHIP**: −0.14 pp, [−0.50, 0.21], p = 0.43 | **NO CLEAR EVIDENCE**: OR 1.20, [1.00, 1.46], p = 0.055 |
| Reproduced from scratch | yes | yes |
| Explored | 7 universes, 22 sandbox checkpoints | 30 universes, 58 sandbox checkpoints |

**The checkout data is synthetic and the answer is planted.** `cases/checkout_ab/generate.py`
sets a true effect of zero and adds internal test accounts (58% conversion, concentrated in the
treatment arm). The plan is hand-written and finds exactly that flip, so this case shows the
mechanics, not discovery. The red-cards flip is a p-value crossing: the odds ratio goes from
1.34 to 1.20 and stays above 1, with p moving from 0.0006 to 0.055. The evidence weakens; the
effect does not reverse. The search favours flips, so this is the nearest crossing Borges
found, not a typical analysis. The robustness share (87% of 30 universes agree) is the fairer
headline. On the red-cards data no single or paired defensible change reverses the finding;
it takes three together. The only single change that would flip it, keeping low-bias referees
only, is rejected by the judge as an indefensible change of population.

### How wide is the curve, against the human teams

| | Borges universes | Reference teams |
|---|---|---|
| Red cards (odds ratio) | 30 universes: 1.20 to 1.36 | 29 teams: 0.89 to 2.93, median 1.31, 20 significant. Two teams (Tobit 2.88, Poisson 2.93) are the extremes; the next highest is 1.71. Ten teams fall inside Borges's range |
| MARP religiosity (standardised beta) | 40 universes: 0.064 to 0.150; all 768 universes enumerated offline: 0.053 to 0.156 | 110 teams: 0.007 to 0.354, median 0.120, all 110 intervals above 0 |
| MARP cultural norms (interaction beta) | 15 universes: 0.018 to 0.046; offline 1,536: -0.002 to 0.049 | 105 teams: -0.045 to 0.282, median 0.039, 68 of 105 above 0 |

Borges's range is narrower than the teams', and it should be. It walks defensible choices
under one estimand: the red-cards plan has four decisions (skin-tone measure, exclusions,
covariates, model family) and 72 base combinations plus the adversary's proposals, while the teams
also chose different outcomes and estimands (Tobit, zero-inflated and negative-binomial
count models, Dirichlet-process clustering, Spearman correlation) and added their own
covariates. The narrower curve answers "how fragile is this analysis within its own
question", not "how much would 29 independent teams disagree". On the real MARP data Borges
also agrees more than the teams do on the cultural-norms question (89% of the 1,536 enumerated universes
against 65% of the teams); the space holds the teams' common choices, not their tails.
Both case READMEs list what is outside the option space.

### A real business case, live only

`bank_marketing_calls` (UCI Bank Marketing, 45,211 phone-campaign records, CC BY 4.0) asks
whether each extra call to a customer lowers the chance of a term-deposit subscription.
Nothing is planted. It has no scripted fixtures and no recording, so it runs only with
`llm=nebius`, and a scripted run is refused with a clear message. It has not been run. Plain
logistic regressions by the author gave an odds ratio of 0.86 to 0.93 per extra call in nine
specifications, so a robust verdict is the expectation; what a live run adds is whether a
defensible fork flips it. See `cases/bank_marketing_calls/README.md`.

### Real, unplanted data: the MARP cases

`marp_religiosity` and `marp_norms` use the Many Analysts Religion Project (10,535
participants in 24 countries, CC-BY 4.0), with the per-team results as the reference lane.
Nobody planted anything. Religiosity and well-being is robust in this option space (no flip
in 40 universes), with a disclosed caveat: well-being options are alternative measures of
overall well-being, and the physical-health facet alone is fragile (see
`cases/marp_religiosity/README.md`). The cultural-norms interaction has one single-change
flip, pooled OLS (p = 0.056, estimate still positive). These recordings are scripted
replays of a hand-built option space seeded from the teams' published choices; the adversary
proposes nothing there.

## Quickstart

Requirements: Python 3.13 with [uv](https://docs.astral.sh/uv/), Node 22+ with pnpm.

```bash
make install          # uv sync --extra contree, pnpm install
make demo-cli         # checkout case end to end, offline and deterministic, $0
make demo-red-cards   # the real red-cards data, offline, $0
uv run --no-sync borges run --case marp_religiosity --llm scripted   # MARP, real data, ~18 s
make serve            # build the web app and serve it on http://127.0.0.1:8000
make test             # ruff, pytest, frontend typecheck, tests and build
```

The web app has a recorded replay of the four recorded cases (the live-only case is listed but has no replay), a "Run it now" button (scripted models,
local subprocess sandboxes) and, when a key is configured and the budget is not spent, "Run
live on Nemotron" (the button says why when it is disabled). The recordings are scripted
(hand-built), not live model runs. The landing page has a "bring your own data" card: it is
enabled only when `/api/health` reports `uploads_available` (a key, budget left, and either
the `contree` backend or `BORGES_ALLOW_UNTRUSTED_LOCAL=true`) and otherwise shows the exact
reason. The same flow is available over the API (`POST /api/uploads`, CSV or parquet, then
`POST /api/runs` with `upload_id`). Uploaded data always needs a live run, which has never
been exercised here.

### Reproduce any universe

Every universe in the drawer carries a command you can paste. For the recorded demos:

```bash
uv sync   # once, from a fresh clone
uv run borges reproduce --case red_cards --universe u_a64c6b99f5
```

(`uv run --no-sync` works too once `uv sync` has run.) It re-executes that universe's steps on the case dataset with the local backend, and prints
`MATCH` only if estimate, interval, p-value, n and verdict equal the recording (exit 1 and
`MISMATCH` otherwise). It also re-runs the baseline, so the flip is shown end to end. Runs
that are not recordings get a downloadable script, `python borges_<run>_<universe>.py --data
path/to/data.parquet`, from `GET /api/runs/{run}/universes/{u}/script`. Universe ids are
read from the recording; the drawer shows the right one.

### Running live on Nemotron (not yet run)

```bash
cp .env.example .env    # then set NEBIUS_API_KEY
make live-smoke         # lists models, one structured call per role, cap 0.05 USD, exit 2 without a key
make record-live        # live-smoke, then record-demo for both curated cases with --llm nebius, then export
```

`make live-smoke` checks the three model ids exist, makes one structured call per role and
reports latency, tokens, cost and finish reason; it fails on a missing id or on reasoning
content leaking when thinking is disabled. `make record-live` runs both demo cases live under
`BORGES_RUN_CAP_USD` (default 0.50), and its recordings replace the scripted ones. Until it
has run, the cost figure in `ARCHITECTURE.md` is an estimate, not a measurement. A single case
can also be run with `uv run borges run --case checkout_ab --llm nebius --record`.

Spend is capped twice, per run (`BORGES_RUN_CAP_USD`, default $0.50) and in total
(`BORGES_SPEND_CAP_USD`, default $5). When the total is used up, the web app disables the
live button and says so. Each call reserves its worst-case cost before it is
sent, so concurrent calls cannot overshoot the cap. Identical requests are served from a
disk cache. `--record` saves every response in the scripted fixture format, so a live run
can be replayed exactly at no cost.

### Running on Nebius Sandboxes

Set `CONTREE_API_KEY` (or reuse `NEBIUS_API_KEY`), `CONTREE_BASE_URL` and, if your account
needs it, `CONTREE_PROJECT_ID`, then pass `--backend contree` (or set
`BORGES_BACKEND=contree` on a server). The ConTree backend is contract-tested, and a live
test runs only when credentials are present; it has never run against the real service, and
there is no hosted demo yet. The first run builds a runner image with the scientific Python stack
once; after that, every analysis step is a non-disposable `image.run` on its parent image,
so each checkpoint is a real sandbox image you can branch from again.

### Docker

```bash
make docker && make docker-run    # one image serves the API and the web app on :8000
```

The image defaults to the scripted model and the local backend, with
`BORGES_ALLOW_UNTRUSTED_LOCAL=false`. Public-deploy settings (see `.env.example`):

| Variable | Purpose |
|---|---|
| `BORGES_ALLOW_UNTRUSTED_LOCAL` | `false` on a public instance: uploads cannot run on the local backend. `make dev` and `make serve` set it to `true` |
| `BORGES_LIVE_TOKEN` | When set, uploads need the header `X-Borges-Live-Token` |
| `BORGES_MAX_ACTIVE_RUNS`, `BORGES_MAX_LIVE_RUNS` | Concurrency limits, 429 beyond them |
| `BORGES_BACKEND` | `contree` for isolated sandboxes |
| `CONTREE_PROJECT_ID` | ConTree project |

Mount a volume on `/app/.borges` (it is declared as a `VOLUME`): the spend ledger lives
there, and without it the live budget resets on every redeploy. Run history is not kept:
`runs/` is not in the image, so old run links stop working after a redeploy.

## How it is built

| Layer | What |
|---|---|
| `analysis` | Planner, coder, adversary, judge and narrator roles; an AST guard that only lets generated code define `apply`/`estimate` and import an exact allowlist; the harness that turns an option into a script carrying state on disk between checkpoints |
| `garden` | Prefix-shared execution with one lock per prefix, beam search over combinations, influence, verification from a fresh root |
| `sandbox` | One fork protocol: `root`, `run(parent) -> child`, `read_file`; local copy-on-write and ConTree backends |
| `llm` | Role routing on Token Factory, JSON-schema output with a fallback, disk cache, reserved spend ledger, scripted replay |
| `runs` | Orchestrator, append-only event log, SSE bus, state fold, replay |
| `api` / `frontend` | FastAPI with SSE; React, TypeScript and D3 |

| Role | Model on Token Factory |
|---|---|
| Planner, adversary, judge | `nvidia/nemotron-3-super-120b-a12b` |
| Coder | `nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B` |
| Narrator | `nvidia/Nemotron-3-Ultra-550b-a55b` |

Details: [ARCHITECTURE.md](ARCHITECTURE.md). Product definition and the end-to-end
definition of done: [PRODUCT.md](PRODUCT.md).

## Security model

- **The server policy is the boundary, not the code guard.** The AST guard
  (default-deny: no underscore attributes, frame and traceback attributes, `type`, `getattr`,
  `exec`, computed string subscripts, and an exact import allowlist) is a lint that stops
  accidents and the bypasses we know of. It is not a sandbox. The generated code comes from a
  model or from an upload.
- **The local backend is not isolation.** It runs each step as a subprocess of the server
  with a scrubbed environment, resource limits and a timeout, and shares the machine's
  filesystem and network. Use it for the scripted demos and on a private machine.
- **Live and upload runs on a shared or public server need the VM backend.** Today the server
  enforces that for uploads: with `BORGES_BACKEND=local` and `BORGES_ALLOW_UNTRUSTED_LOCAL`
  not true, `POST /api/runs` with an `upload_id` is refused (400). Live runs on a curated
  case are not refused on the local backend by the server, although the coder then writes
  the code that runs; do not expose that combination publicly. Set `BORGES_BACKEND=contree`.
- The server, not the client, picks the backend, clamps `max_universes`, limits concurrency
  (429), refuses live runs without a key (400) or past the spend cap (403), and can require
  `X-Borges-Live-Token` for uploads. The built-in UI does not send that header.
- Never commit `.env`. CI (`.github/workflows/ci.yml`) runs lint, tests and the frontend
  build; a badge will exist once the repository is public.

## Related work

The closest open implementation is
[amazon-science/agentic-forking-path](https://github.com/amazon-science/agentic-forking-path)
(the code of "Many AI analysts, one dataset", Bertran, Fogliato and Wu): persona agents each
run a whole independent analysis and an LLM extracts the forks afterwards, where Borges forks
a shared checkpointed execution and has an adversary propose forks. It has been run live at
scale; Borges has not, and no head-to-head exists. Boba, `multiverse`, `specr` and ForkSCOPE
are compared in [PRODUCT.md](PRODUCT.md#related-work), with links and with what Borges does
not do better.

## What Borges does not claim

Influence is an interventional contrast under a fixed continuation protocol, not a causal
statement about the world. Borges explores the defensible space that its planner and
adversary propose, not every possible analysis. The robustness share is computed over the
universes it explored, and the search deliberately favours universes likely to flip.
Specification-curve and multiverse analysis are established ideas (Simonsohn et al. 2020;
Steegen et al. 2016); what is new here is agents that discover the alternatives, fork real
execution state mid-analysis, search for the smallest flip and prove it reproduces. That claim
rests on a design that has been tested with scripted agents; whether Nemotron proposes good
forks is untested until the first live run.

## Data

- **Checkout A/B**: synthetic, generated by `cases/checkout_ab/generate.py` with a planted
  effect.
- **Red cards**: the Crowdstorming dataset by Silberzahn et al., real, CC0 1.0 on the
  [OSF (gvm2z)](https://osf.io/gvm2z/). See `cases/red_cards/README.md`.
- **Bank marketing**: UCI Bank Marketing (Moro, Rita and Cortez, 2014), real, CC BY 4.0,
  [doi:10.24432/C5K306](https://doi.org/10.24432/C5K306). See
  `cases/bank_marketing_calls/README.md`.
- **MARP**: Many Analysts Religion Project data and team results, real, CC-BY 4.0 (Hoogeveen,
  Sarafoglou, Aczel et al., 2022; OSF [qbdce](https://osf.io/qbdce/) and
  [gkxqy](https://osf.io/gkxqy/)). See `cases/marp_*/README.md`.

The scripted fixtures were built by hand from computed numbers: each `build_fixtures.py`
runs the option code on the data and writes the planner, coder, adversary, judge and narrator
responses, so every figure they state is computed, but no model wrote them.

## License

Apache-2.0.
