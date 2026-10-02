# Borges

**How fragile or robust is this decision, and which analytic choice matters? Borges re-runs
the analysis along other defensible paths, tells you how many agree with yours, and shows the
smallest flip it found.**

> ## Judge it in 2 minutes
>
> **What Borges answers:** how fragile or robust a data decision is, and which analytic choice
> moves it. It leads with the share of explored paths that agree with yours ("N of M paths
> agree"), then the smallest flip it found and which kind it is: a *direction* flip (the sign
> reverses) or only a *significance* flip (same sign, p crosses 0.05).
>
> - Hosted demo: TODO-OWNER (URL, none exists yet)
> - Video: TODO-OWNER (link, not recorded yet)
> - Offline, no key, from a fresh clone (Python 3.13 and [uv](https://docs.astral.sh/uv/)):
>
> ```bash
> uv sync
> uv run borges run --case marp_norms --llm scripted
> uv run borges reproduce --case checkout_ab --source live --universe u_3a4a8a35a5
> ```
>
> The first is an offline scripted replay and ends with `Universes: 15, checkpoints: 67, LLM
> calls: 24 scripted (0 cached)` and `cost: $0.0000 (scripted replay, no model called)`: the
> data, the code and every statistic are real, no model wrote the plan. The second
> re-executes a universe from the live Nemotron recording of the checkout case and prints
> `MATCH` when the result equals the recording. All five cases were recorded live on 2
> October 2026 for $0.0145 to $0.0326 each; the web app plays those recordings by default.
> The status table below says what is and is not live.
>
> **The value:** one analysis is one path. Borges shows the other defensible paths, how many
> agree, and, with a calibration study (`evidence/calibration.md`), how much to trust a flip.

<p align="center"><img src="assets/screenshots/replay-1280.png" alt="Borges replay of the red cards case at 1280 px: the garden of forking paths, the flipped verdict and the spec curve" width="760"> <img src="assets/screenshots/replay-390.png" alt="The same replay at 390 px wide" width="170"></p>

<sub>Screenshots of the scripted replay of the red cards case (no model called); the drawer view is in `assets/screenshots/replay-drawer-1280.png`. The web app plays the live Nemotron recording by default.</sub>

In three lines:

1. You give it a dataset, a question and the rule you will act on ("ship if the lift is
   positive with p < 0.05").
2. Nemotron plans the analysis, every choice forks a real sandbox, and an adversary proposes
   paths against your conclusion.
3. You get the share of universes that agree, the decisions that move the result, the
   smallest flip found by a bounded search (and whether it reverses the sign or only crosses
   p = 0.05), and a command that reproduces it.

Built for the [Nebius x NVIDIA Global AI Hackathon](https://nebiusglobalaihackathon.devpost.com/)
on **NVIDIA Nemotron 3** served by **Nebius Token Factory**. Every analysis step runs as a
branch of a sandbox: a local subprocess backend by default (no VM isolation), or Nebius
Token Factory Sandboxes (ConTree, VM-isolated) with `BORGES_BACKEND=contree`.

## Status: what has and has not run

Be clear about this before reading further. The source of truth for every live number is
[evidence/live-runs.md](evidence/live-runs.md).

| | State today |
|---|---|
| Nemotron through Token Factory | **Ran live on 2 October 2026, all five cases, from an empty cache.** 150 calls in the five recordings (24, 32, 22, 31, 41), $0.0145 to $0.0326 per case. Models: `nvidia/nemotron-3-super-120b-a12b` (planner, adversary, judge, repairer, reviewer), `nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B` (coder), `nvidia/Nemotron-3-Ultra-550b-a55b` (narrator). The whole development day made 45 live runs, 31 completed, $0.65 recorded ($0.76 in the spend ledger with smoke checks) |
| What the web app plays | The live recordings in `cases/<case>/recorded-live/events.jsonl`, by default, under the banner "Recorded live on Nemotron via Nebius Token Factory, <date>: <calls> calls, <tokens> tokens, $<cost>". A toggle switches to the scripted replay where one exists |
| Scripted replays | Still shipped: hand-built fixtures, not model output, labelled `scripted` (or `scripted-fixture`), 0 tokens and $0. The CLI says so: `cost: $0.0000 (scripted replay, no model called)`. They are the offline path and what the calibration and grid studies use |
| What is real | The data, the option code, the sandbox execution and every statistic. `borges reproduce --source live` re-executed a recorded live universe from scratch for all five cases and matched |
| ConTree sandboxes | Implemented against `contree-sdk` and contract-tested with a fake SDK. The live test is skipped without credentials. **Still never run against the real service**: every live run above used the local subprocess backend |
| Hosted public demo | **None yet**: no public URL, no video |
| Outside users | None. Nobody outside the project has used it, and no head-to-head against another tool exists |

The scripted recordings (`cases/*/recorded/events.jsonl`) still list the configured role model
ids in the `run.started` `models` field, even though no model was called; the `llm` field of
the same event says `scripted`.

### The five live recordings

| Case | Calls | Tokens in / out | Cost | Original verdict | Smallest flip found |
|---|---|---|---|---|---|
| checkout_ab | 24 | 38,219 / 6,055 | $0.0145 | DON'T SHIP: lift -0.13 pp [-0.79, +0.53] | Keep internal and bot-like sessions: +0.84 pp, SHIP (direction) |
| red_cards | 32 | 57,433 / 7,318 | $0.0183 | BIAS DETECTED: OR 1.34 [1.14, 1.58] | none in 9 universes |
| marp_religiosity | 22 | 66,078 / 5,201 | $0.0191 | POSITIVE ASSOCIATION: beta 0.090 [0.073, 0.107] | none in 24 universes |
| marp_norms | 31 | 94,401 / 6,465 | $0.0266 | DEPENDS ON NORMS: interaction 0.036 [0.019, 0.052] | none in 32 universes |
| bank_marketing_calls | 41 | 86,266 / 13,975 | $0.0326 | CAP THE CALLS: OR 0.878 per call [0.863, 0.892] | Listwise deletion plus robust SE: OR 0.88 [0.61, 1.27], p 0.50 (significance only) |

Run ids, universe counts and the reproduce results are in `evidence/live-runs.md`. In the
checkout case nobody scripted the plan: Nemotron found the planted internal-traffic artefact
on its own. The live red-cards OR matches the default analysis the case cites. A single live
run per case is one sample of a model: it is not a measure of how often Nemotron finds a flip.

### What the live runs taught us

The first live batches failed in ways the scripted demos could not show, and each failure
became a safeguard with a test.

- **Standard errors 50 times too small.** The checkout fit reported -0.14 pp with a 95% CI of
  [-0.145, -0.138] and p = 0. A split-half standard error check now re-estimates on random
  halves and rejects intervals far too narrow, and (after a CI of [-341, +341] pp) far too wide.
- **A flip to -398,439.** A broken Bayesian option produced an absurd estimate that counted as
  a flip. Implausible estimates are now failed universes, never flips.
- **A label that did not match the estimator.** The plan said "Firth's penalized logistic
  regression" and the code was a plain Logit with an unseeded bootstrap, so the run did not
  reproduce. Randomness is now seeded, the planner may only name estimators that statsmodels
  or scipy provide, and Nemotron Super reviews every option, adversary options included,
  against the estimator it names.
- **A ratio rule on the wrong scale.** The bank case judged a log-odds coefficient (-0.116)
  against "odds ratio < 1", so no universe could ever flip. A ratio rule now requires
  positive estimates and intervals, and the coder is told the scale.
- **A sign that meant nothing.** A mirror flip (+0.037 to -0.037 on the same rows) came from
  an unoriented PCA score, and a "control indicator" option only reversed the sign. Smoke
  runs now report observed effects and a deterministic orientation check fails reversed columns.
- **Columns that never existed.** Steps now declare the names they produce, aggregations
  carry group-constant columns along, and model steps start from complete cases.

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

The numbers in this section and in the next two come from the scripted replays of the hand-built
option spaces (the offline path). The live recordings above reached their own verdicts, for
example DON'T SHIP for the checkout case as run, and are summarised in the status section and
in `evidence/live-runs.md`.

| | Checkout A/B test (synthetic, effect planted) | Red cards (real data, 146,028 dyads) |
|---|---|---|
| Question | Does the new checkout increase conversion? | Do referees give dark-skinned players more red cards? |
| Default analysis | **SHIP**: +0.53 pp, 95% CI [0.14, 0.92], p = 0.008 | **BIAS DETECTED**: OR 1.34, 95% CI [1.13, 1.58], p = 0.0006 |
| Smallest flip found | 1 change: exclude internal test accounts | 3 changes together: the second rater only, referees with 22+ dyads, full covariates |
| Flipped result | **DON'T SHIP**: −0.14 pp, [−0.50, 0.21], p = 0.43 | **NO CLEAR EVIDENCE**: OR 1.20, [1.00, 1.46], p = 0.055 |
| Reproduced from scratch | yes | yes |
| Explored | 7 universes, 22 sandbox checkpoints | 30 universes, 58 sandbox checkpoints |

**The checkout data is synthetic and the answer is planted.** `cases/checkout_ab/generate.py`
sets a true effect of -0.2 pp (`TRUE_EFFECT = -0.0020`), adds a +0.4 pp novelty bump to the
treatment arm on days 0-2 (`NOVELTY_BUMP = 0.004`) and adds internal test accounts (58%
conversion, assigned to treatment with probability 0.80). The plan is hand-written and finds exactly that flip, so this case shows the
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
Nothing is planted. It has no scripted fixtures, so it runs only with `llm=nebius`, and a
scripted run is refused with a clear message. Its only recording is the live one. Plain
logistic regressions by the author gave an odds ratio of 0.86 to 0.93 per extra call in nine
specifications. The live run (41 calls, $0.0326) gave OR 0.878 per call [0.863, 0.892], CAP
THE CALLS, and found a significance-only flip: listwise deletion of rows with any missing
covariate (45,211 to 7,842 rows) with robust standard errors gives OR 0.88 [0.61, 1.27], p
0.50. See `cases/bank_marketing_calls/README.md`.

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

The web app plays the live recording of each of the five cases by default, with a toggle to the
scripted replay for the four cases that have one (the bank case is live-only). It also has a "Run it now" button (scripted models,
local subprocess sandboxes) and, when a key is configured and the budget is not spent, "Run
live on Nemotron" (the button says why when it is disabled). The landing page has a "bring your own data" card: it is
enabled only when `/api/health` reports `uploads_available` (a key, budget left, and either
the `contree` backend or `BORGES_ALLOW_UNTRUSTED_LOCAL=true`) and otherwise shows the exact
reason. The same flow is available over the API (`POST /api/uploads`, CSV or parquet, then
`POST /api/runs` with `upload_id`). Uploaded data always needs a live run; the upload path
has not been exercised with a live model, only the five curated cases have.

### Reproduce any universe

Every universe in the drawer carries a command you can paste. For the scripted demos and for
the live recordings:

```bash
uv sync   # once, from a fresh clone
uv run borges reproduce --case red_cards --universe u_a64c6b99f5
uv run borges reproduce --case checkout_ab --source live --universe u_3a4a8a35a5
```

`--source live` reads `cases/<case>/recorded-live/events.jsonl` instead of the scripted
recording and re-executes that universe's code from scratch. It matched for all five cases
(universe ids and results in `evidence/live-runs.md`).

(`uv run --no-sync` works too once `uv sync` has run.) It re-executes that universe's steps on the case dataset with the local backend, and prints
`MATCH` only if estimate, interval, p-value, n and verdict equal the recording (exit 1 and
`MISMATCH` otherwise). It also re-runs the baseline, so the flip is shown end to end. Runs
that are not recordings get a downloadable script, `python borges_<run>_<universe>.py --data
path/to/data.parquet`, from `GET /api/runs/{run}/universes/{u}/script`. Universe ids are
read from the recording; the drawer shows the right one.

### Running live on Nemotron

```bash
cp .env.example .env    # then set NEBIUS_API_KEY
make live-smoke         # lists models, one structured call per role, cap 0.05 USD, exit 2 without a key
make record-live        # live-smoke, then each case live with --llm nebius, written to cases/<case>/recorded-live/
```

`make live-smoke` checks the model ids exist, makes one structured call per role and
reports latency, tokens, cost and finish reason; it fails on a missing id or on reasoning
content leaking when thinking is disabled. `make record-live` runs the cases live under
`BORGES_RUN_CAP_USD` (default 0.50) and writes each recording to
`cases/<case>/recorded-live/`. It never overwrites the scripted recordings in
`cases/<case>/recorded/`. A single case can also be run with
`uv run borges run --case checkout_ab --llm nebius --record`. A complete live run of one case
cost between $0.015 and $0.033 on 2 October 2026.

Spend is capped twice, per run (`BORGES_RUN_CAP_USD`, default $0.50) and in total
(`BORGES_SPEND_CAP_USD`, default $5). When the total is used up, the web app disables the
live button and says so. Each call reserves its worst-case cost before it is
sent, so concurrent calls cannot overshoot the cap. Identical requests are served from a
disk cache. `--record` saves every response in the scripted fixture format, so a live run
can be replayed exactly at no cost.

### Running on Nebius Sandboxes

Set `NEBIUS_API_KEY` (the same Token Factory key; `CONTREE_API_KEY` overrides it) and
`NEBIUS_PROJECT_ID` (from tokenfactory.nebius.com/project/api-keys), then pass
`--backend contree` (or set `BORGES_BACKEND=contree` on a server). The endpoint defaults to
`https://api.tokenfactory.nebius.com/sandboxes/`; `CONTREE_BASE_URL` overrides it. The ConTree backend is contract-tested, and a live
test runs only when credentials are present; it has never run against the real service (the
live Nemotron runs used the local backend), and there is no hosted demo yet. The first run builds a runner image with the scientific Python stack
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
| `BORGES_ALLOW_UNTRUSTED_LOCAL` | `false` on a public instance: uploads cannot run on the local backend. `make dev` sets it to `true`; `make serve` does not |
| `BORGES_LIVE_TOKEN` | Deprecated alias, kept so old setups hold: a request carrying this value in `X-Borges-Live-Token` is treated as a key with `uploads:write` and `runs:create:live:upload`. New setups should use API keys (below) |
| `BORGES_ANON_ACTIVE_RUNS`, `BORGES_ANON_RUNS_PER_MIN`, `BORGES_ANON_LIVE_RUNS_PER_HOUR` | Per-client run quota for anonymous callers: concurrent runs, scripted starts per minute, live starts per hour (429 with `Retry-After`) |
| `BORGES_RATE_ANON_BURST`, `BORGES_RATE_ANON_PER_S`, `BORGES_RATE_KEY_BURST`, `BORGES_RATE_KEY_PER_S` | Token-bucket rate limits per principal (anonymous callers are limited per client address and stricter); 429 with `Retry-After` beyond them |
| `BORGES_REGISTRY_FOUR_EYES` | `true`: a version cannot be approved by the principal that published it, and `borges agents approve` needs a key with `registry:approve` |
| `BORGES_AUDIT_ANCHOR_KEY`, `BORGES_AUDIT_ANCHOR_EVERY` | HMAC key and record interval for the signed checkpoints of the global audit chain |
| `BORGES_MAX_ACTIVE_RUNS`, `BORGES_MAX_LIVE_RUNS` | Concurrency limits, 429 beyond them |
| `BORGES_BACKEND` | `contree` for isolated sandboxes |
| `NEBIUS_PROJECT_ID` | Token Factory project for Sandboxes (`CONTREE_PROJECT_ID` overrides it) |

Mount a volume on `/app/.borges` (it is declared as a `VOLUME`): the spend ledger lives
there, and without it the live budget resets on every redeploy. Run history is not kept:
`runs/` is not in the image, so old run links stop working after a redeploy.

### Access control

Every `/api` request resolves to a principal. With no credentials that is `caller://anonymous`,
which holds exactly the public-demo scopes (`cases:read`, `runs:read`, `runs:create:scripted`,
`runs:create:live:curated`, `recordings:read`): hackathon judges browse, watch recordings and
start scripted or curated live runs with no login. Everything else needs a named API key
(`Authorization: Bearer bk_...`); the web app has a field in its header to paste one, kept in
`sessionStorage`.

```bash
uv run borges keys create --name ci --scopes uploads:write,runs:create:live:upload --expires 30d
uv run borges keys list
uv run borges keys revoke <key_id>
```

Keys live in an append-only, hash-chained store under `BORGES_HOME/identity/` and only their salted
hashes are kept; the secret is printed once. `GET /api/me` shows the current principal, its scopes
and its rate-limit state; `GET /api/audit` (scope `audit:read`) reads the global audit chain.
Every route declares its required scope in one table and an undeclared route is denied.
Details and limits: [SECURITY.md](SECURITY.md).

### Gateway policy

`policy/gateway.json` says, per agent, which models it may call (primary and fallback chain),
its `max_tokens` ceiling, calls, cost and concurrency per run, and which data it may receive
(`profile_only`, `sample_rows` with a bound, or `none`); it also says who may run what in the
sandbox. Every model call and sandbox execution goes through `src/borges/gateway/`, which
checks the agent token, the capability, the egress class and the budgets, retries transient
errors with backoff, trips a per-model circuit breaker and falls back only along the listed
chain. The policy's sha is in every run's provenance; `GET /api/policy` and the Fleet page show
it. Changing the file changes the agents' definitions, so publish and approve a new registry
version (`borges agents publish --approve`).

### Model Armor

`src/borges/armor/` is the inline guardrail layer, plugged into the gateway's armor-in and
armor-out hooks and into run creation and uploads. It refuses runs whose question, rule text,
file or column names carry instructions, quarantines instruction-like column notes and cell
values (with a caveat on the run page), drops model-proposed options that try to steer the
result or the code, and redacts personal data (e-mail, phone, cards, IBAN, SSN, DNI/NIE,
CURP/RFC, IP, dates of birth) before any model sees it. The upload response and screen list the
columns that contain personal data, with counts. Set `BORGES_ARMOR_LLM=true` to add a
judge-model second stage for ambiguous text. Details and limits are in `SECURITY.md`.

## How it is built

| Layer | What |
|---|---|
| `analysis` | Planner, coder, adversary, judge, reviewer and narrator roles; an AST guard that only lets generated code define `apply`/`estimate` and import an exact allowlist; the harness that turns an option into a script carrying state on disk between checkpoints |
| `garden` | Prefix-shared execution with one lock per prefix, beam search over combinations, influence, verification from a fresh root |
| `sandbox` | One fork protocol: `root`, `run(parent) -> child`, `read_file`; local copy-on-write and ConTree backends |
| `llm` | Role routing on Token Factory, JSON-schema output with a fallback, disk cache, reserved spend ledger, scripted replay |
| `runs` | Orchestrator, append-only event log, SSE bus, state fold, replay |
| `api` / `frontend` | FastAPI with SSE; React, TypeScript and D3 |

| Role | Model on Token Factory |
|---|---|
| Planner, adversary, judge, repairer | `nvidia/nemotron-3-super-120b-a12b` |
| Reviewer: checks every option's code, adversary options included, against its spec, the estimator it names and the effects observed in the smoke run | `nvidia/nemotron-3-super-120b-a12b` |
| Coder | `nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B` |
| Narrator | `nvidia/Nemotron-3-Ultra-550b-a55b` |

Details: [ARCHITECTURE.md](ARCHITECTURE.md). Product definition and the end-to-end
definition of done: [PRODUCT.md](PRODUCT.md).

## Security model

Generated code runs behind three layers: an AST code guard (a lint), a runtime audit-hook policy
embedded in every step (no process creation, no network, writes only inside the step directory,
reads limited to an allowlist that denies `.env`, `/proc/*/environ` and the user's home), and VM
isolation on ConTree. The local backend is not an isolation boundary, and uploads are refused on
it unless `make dev` allows them. Full model and its limits: [SECURITY.md](SECURITY.md).

## How much to trust a flip

`evidence/calibration.md` (offline, scripted, 504 synthetic checkout datasets of about 30,000
sessions, the real pipeline, fixed menu of 5 steps x 2 options plus one scripted adversary
option, seeds `20261002 + cell_index * 1,000,000 + i`, Wilson 95% intervals; nothing live):

| Situation | Flip reported | Direction flip |
|---|---|---|
| Large true effect (0.010 absolute lift), no artefact, n = 80 | 13/80 = 16% [10, 26] | 0/80 [0, 5] |
| Null effect, default analysis wrongly says SHIP, n = 80 | 71/80 = 89% [80, 94] | 0/80 [0, 5] |
| Null effect with the planted artefact, n = 80 | 78/80 = 98% [91, 99]; via internal traffic 76/80 = 95% [88, 98] | 35/80 = 44% [33, 55] |
| True effect at 80% power with the artefact, n = 80 | via internal traffic 55/80 = 69% [58, 78] | 0/80 [0, 5] |

The uncomfortable conclusion: on clean data with a large true effect the search reports a
significance-only flip 16% of the time, and in 272 clean datasets it never reported a
direction flip (95% upper bound about 1.4%). A flip label must say which kind it is. A
significance flip is weak evidence (it is expected from noise near the threshold); a direction
flip is specific. The red-cards flip (OR 1.34 to 1.20) is of the weak kind. No flip does not
prove no artefact: detection falls as the true effect grows (95%, 69%, 21%). The rates apply to
this fixed menu, not to arbitrary datasets.

Against a fixed full grid (what a hand-written multiverse or specr would run over the same
seeded options), `evidence/grid_vs_search.md`: the grid ran 72, 32, 768 and 1,536 universes on
red cards, checkout, MARP religiosity and MARP norms (27, 12, 204 and 424 s offline) and found
the same smallest flip as Borges in all four cases, or none in either. Borges used 30, 7, 40 and
15 universes. The objections a statistician would raise, with answers, are in `PRODUCT.md`.

## Related work

The closest open implementation is
[amazon-science/agentic-forking-path](https://github.com/amazon-science/agentic-forking-path)
(the code of "Many AI analysts, one dataset", Bertran, Fogliato and Wu): persona agents each
run a whole independent analysis and an LLM extracts the forks afterwards, where Borges forks
a shared checkpointed execution and has an adversary propose forks. It has been run live at
scale (about 5,000 analyst runs); Borges has five live recordings, and no head-to-head exists. Boba, `multiverse`, `specr` and ForkSCOPE
are compared in [PRODUCT.md](PRODUCT.md#related-work), with links and with what Borges does
not do better.

## What Borges does not claim

Influence is an interventional contrast under a fixed continuation protocol, not a causal
statement about the world. Borges explores the defensible space that its planner and
adversary propose, not every possible analysis. The robustness share is computed over the
universes it explored, and the search deliberately favours universes likely to flip. The live
runs are one recording per case: they show that Nemotron can plan, fork and be reproduced, not
how often it finds a given flip.
Specification-curve and multiverse analysis are established ideas (Simonsohn et al. 2020;
Steegen et al. 2016); what is new here is agents that discover the alternatives, fork real
execution state mid-analysis, search for the smallest flip and prove it reproduces. That claim
rests on a design that was tested with scripted agents and then run live once per case on
Nemotron (`evidence/live-runs.md`). Five recordings show it works end to end and reproduces;
they do not show that Nemotron's forks are reliably good, and there is no outside user yet.

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

The scripted fixtures (the offline path) were built by hand from computed numbers: each `build_fixtures.py`
runs the option code on the data and writes the planner, coder, adversary, judge and narrator
responses, so every figure they state is computed, but no model wrote them.

## License

Apache-2.0.
