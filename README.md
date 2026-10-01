# Borges

**Every conclusion is one path through a garden of forking analyses. Borges walks the
others, and shows you the one defensible choice that flips your decision.**

Built for the [Nebius x NVIDIA Global AI Hackathon](https://nebiusglobalaihackathon.devpost.com/)
on **NVIDIA Nemotron 3** served by **Nebius Token Factory**. Every analysis step runs as a
branch of a sandbox: a local subprocess backend by default (no VM isolation), or Nebius
Token Factory Sandboxes (ConTree, VM-isolated) with `BORGES_BACKEND=contree`.

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
4. **Borges finds the minimal defensible flip.** It tries one change, then two, then three,
   always running first the combinations that moved the result closest to the threshold.
   It then re-executes the winning universe from a fresh sandbox to prove it reproduces.
5. **You can step into any universe** and see its exact code, row counts, checkpoint ids
   and result.

## The two demo cases

| | Checkout A/B test (synthetic) | Red cards (real data, 146,028 dyads) |
|---|---|---|
| Question | Does the new checkout increase conversion? | Do referees give dark-skinned players more red cards? |
| Default analysis | **SHIP**: +0.53 pp, 95% CI [0.14, 0.92], p = 0.008 | **BIAS DETECTED**: OR 1.34, 95% CI [1.13, 1.58], p = 0.0006 |
| Minimal flip | 1 change: exclude internal test accounts | 3 changes together: the second rater only, referees with 22+ dyads, full covariates |
| Flipped result | **DON'T SHIP**: −0.14 pp, [−0.50, 0.21], p = 0.43 | **NO CLEAR EVIDENCE**: OR 1.20, [1.00, 1.46], p = 0.055 |
| Reproduced from scratch | yes | yes |
| Explored | 7 universes, 22 sandbox checkpoints | 30 universes, 58 sandbox checkpoints |

In the checkout case the new checkout truly does nothing: employee and QA test orders,
concentrated in the treatment arm, create the lift. Borges finds that this one decision
moves the estimate more than any other. On the red-cards data no single or paired
defensible change reverses the finding; it takes three together. The only single change
that would flip it, keeping low-bias referees only, is rejected by the judge as an
indefensible change of population. The 29 human teams' estimates are overlaid on the
specification curve.

## Quickstart

Requirements: Python 3.13 with [uv](https://docs.astral.sh/uv/), Node 22+ with pnpm.

```bash
make install          # uv sync --extra contree, pnpm install
make demo-cli         # checkout case end to end, offline and deterministic, $0
make demo-red-cards   # the real red-cards data, offline, $0
make serve            # build the web app and serve it on http://127.0.0.1:8000
make test             # ruff, pytest, frontend typecheck, tests and build
```

The web app has a recorded replay of both cases, a "Run it now" button (scripted models,
local subprocess sandboxes) and, when a key is configured and the budget is not spent, "Run
live on Nemotron" (curated cases only; the button says why when it is disabled). The hosted
demo replays a recorded run and runs scripted. Uploading your own dataset is API-only
(`POST /api/uploads`, then `POST /api/runs` with `upload_id`), needs live mode, and on a
public instance needs `BORGES_BACKEND=contree` and `BORGES_LIVE_TOKEN`.

### Running live on Nemotron

```bash
cp .env.example .env    # then set NEBIUS_API_KEY
uv run borges run --case checkout_ab --llm nebius --record
```

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
test runs only when credentials are present; the hosted demo does not use it. The first run builds a runner image with the scientific Python stack
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
| `BORGES_ALLOW_UNTRUSTED_LOCAL` | `false` on a public instance: uploads cannot run live on the local backend. `make dev` and `make serve` set it to `true` |
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

## What Borges does not claim

Influence is an interventional contrast under a fixed continuation protocol, not a causal
statement about the world. Borges explores the defensible space that its planner and
adversary propose, not every possible analysis. The robustness share is computed over the
universes it explored, and the search deliberately favours universes likely to flip.
Specification-curve and multiverse analysis are established ideas (Simonsohn et al. 2020;
Steegen et al. 2016); what is new here is agents that discover the alternatives, fork real
execution state mid-analysis, search for the minimal flip and prove it reproduces.

## Data

The red-cards data is the Crowdstorming dataset by Silberzahn et al., released under
CC0 1.0 on the [OSF (gvm2z)](https://osf.io/gvm2z/). See `cases/red_cards/README.md`.

## License

Apache-2.0.
