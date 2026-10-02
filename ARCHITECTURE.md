# Borges — architecture

## 1. Shape of the system

```
 React app (Vite, TS, D3)  ──SSE /api/runs/{id}/events──►  FastAPI (borges.api)
        ▲                                                      │
        │ static build served by FastAPI                       ▼
        │                                         RunOrchestrator (borges.runs)
        │                                                      │
        │      ┌───────────────┬──────────────────┬────────────┴──────────┐
        │      ▼               ▼                  ▼                       ▼
        │  analysis.*      garden.*           llm.*                  sandbox.*
        │  planner         executor           LLMClient              BranchBackend
        │  coder           search             nebius / scripted      local / contree
        │  adversary       influence          disk cache, spend      checkpoint fork
        │  judge           verify             guard
        │  narrator
        └── runs/<id>/events.jsonl  (every run is an append-only event log; replay = re-stream)
```

One Python package `borges` (in `src/borges`), domain-driven: each domain owns its models,
logic and tests. Files stay under ~200 lines. The frontend lives in `frontend/` and is built
into `frontend/dist`, which FastAPI serves at `/`.

## 2. Domains

| Domain | Responsibility | Key files |
|---|---|---|
| `analysis` | The plan (steps, options, decision rule), the LLM roles that create and judge it, the harness that turns an option into executable code | `models.py`, `planner.py`, `coder.py`, `adversary.py`, `judge.py`, `narrator.py`, `code_guard.py`, `code_guard_introspection.py`, `harness.py`, `profile.py` |
| `garden` | Universes, prefix-shared execution, bounded flip search, influence, verification | `models.py`, `executor.py`, `search.py`, `influence.py`, `verify.py` |
| `sandbox` | Branchable execution backends behind one protocol | `backend.py`, `local_backend.py`, `contree_backend.py`, `factory.py` |
| `llm` | Role-based model routing, structured JSON output, disk cache, cost accounting, hard spend cap | `client.py`, `nebius_provider.py`, `scripted_provider.py`, `cache.py`, `spend.py`, `json_output.py`, `factory.py` |
| `runs` | Orchestration, event bus, run store, replay, state folding | `events.py`, `orchestrator.py`, `bus.py`, `store.py`, `replay.py`, `state.py` |
| `cases` | Curated demo cases (dataset + pinned plan + hand-built scripted model responses) | `registry.py`, plus `cases/<id>/` data folders |
| `api` | HTTP + SSE + static UI | `app.py`, `routes_*.py`, `schemas.py` |

## 3. The execution model (the core idea)

**Option code contract.** Each option is a Python function body. Non-final steps implement
`def apply(df, ctx) -> df`. The final step (`kind == "model"`) implements
`def estimate(df, ctx) -> dict` and returns `estimate, ci_low, ci_high, p_value, n`.
`ctx` is a JSON-serialisable dict that carries decisions forward (e.g. a covariate list
chosen at step 3 and read by the model at step 5). Allowed imports: pandas, numpy,
scipy(.stats), statsmodels(.api/.formula.api), math. `code_guard` enforces this with an AST
allowlist. The guard is default-deny (underscore attributes, frame and traceback
attributes, `type`, `getattr`, `exec`, computed string subscripts) and is a lint, not a
sandbox. It stops accidents and the bypasses reviewers have found so far (covered by
`tests/analysis/test_code_guard_introspection.py` and, for formula strings, by the formula
check in `code_guard_formula.py`), but it is a pattern check on source text and is not
claimed to be complete: code built from split or computed strings can be an escape route. The
isolation boundary is the backend and the server policy (section 7).

**Harness.** `harness.render_step(step, option)` produces a self-contained script. It
loads `state/df.parquet` (or the root `data.parquet` on the first step) and `state/ctx.json`,
runs the option, writes the state back, and prints machine-readable lines:
`BORGES_TRACE {...}` with row counts, and on the final step `BORGES_RESULT {...}`. State lives
on the filesystem because ConTree checkpoints capture the filesystem, not RAM.

**Checkpoints.** The sandbox root holds the dataset and is checkpoint `R`. Running step *i*
with option *o* on checkpoint *P* yields a new checkpoint. A universe is a full choice vector
`{step_id: option_id}`. Its path is the chain of checkpoints for its successive prefixes.

**Prefix sharing.** `garden.executor` keeps `prefix -> Checkpoint`, with a per-key async lock
so concurrent universes never recompute a shared prefix. The baseline and all single-flip
universes share every checkpoint before the step they change.

**Search order** (bounded by `max_universes`):
1. baseline (all defaults);
2. single flips (one non-default option, defaults elsewhere);
3. adversary round: new options from real intermediate state, judged for defensibility,
   then single flips of the accepted ones;
4. combination flips, only while no flip has been found: a beam search by level. Level *k*
   extends every finished universe with *k − 1* changes by one more single change, ranks the
   candidates by the measured movement toward the opposite verdict of the parent plus that
   of the added change, and runs the top ten. It stops at the first level that flips, or
   when the universe budget is spent;
5. verification of the smallest flip found: re-execution from the root with no prefix cache, and
   the result must match exactly.

**Smallest flip found** = the flipped universe with the fewest changes among those the capped search (ten combinations per level, `MAX_COMBINATIONS_PER_LEVEL`) explored; it is not a proven minimum. Ties go to the higher
minimum defensibility, then to the larger move of the estimate.

**Influence** of a decision = the mean absolute change in the estimate when that decision
alone is switched away from the default, all else held at defaults. This is an
interventional contrast under a fixed continuation protocol, not a causal claim about the
world.

## 4. Models and money

| Role | Model (Token Factory id) | Calls per run |
|---|---|---|
| planner | `nvidia/nemotron-3-super-120b-a12b` | 1 |
| coder | `nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B` | 1 per option (+1 repair max) |
| adversary | `nvidia/nemotron-3-super-120b-a12b` | 1 |
| judge | `nvidia/nemotron-3-super-120b-a12b` | 1 per adversary option |
| narrator | `nvidia/Nemotron-3-Ultra-550b-a55b` | 1 |

**No live cost has been measured.** Nothing has run on Token Factory yet. The earlier figure
of about $0.02-0.05 per run was an estimate from the price table, not a measurement, and is
withdrawn until `make record-live` produces one (TODO-LIVE). The scripted runs report 0
tokens and $0. Money controls:
- a content-addressed disk cache (`.borges/llm-cache/`), so repeated development runs are free;
- a persistent spend ledger (`.borges/spend.json`) with a hard cap (`BORGES_SPEND_CAP_USD`),
  which raises before any call that would exceed it;
- tests and the offline demo use the scripted provider and cost nothing;
- `max_tokens` is set on every call.

## 5. Events (the contract between backend and UI)

Every run is an append-only stream of `{seq, ts, run_id, type, data}`. The UI folds events
into state, and replay is the same stream re-emitted from `runs/<id>/events.jsonl`. Types are
defined in `borges/runs/events.py` and mirrored in `frontend/src/shared/types/contracts.ts`.

Payloads (`data`), always JSON from `model_dump(mode="json")`:

| type | data |
|---|---|
| `run.started` | `RunStartedData` |
| `stage` | `StageData` |
| `plan.ready` | `{"plan": AnalysisPlan}` |
| `option.coded` | `OptionCodedData` |
| `option.proposed` | `{"step_id": str, "option": Option}` |
| `option.judged` | `OptionJudgedData` |
| `checkpoint.created` | `CheckpointCreatedData` (root: `parent_id`, `step_id`, `option_id` null, `depth` 0) |
| `universe.started` / `universe.finished` | `{"universe": Universe}` |
| `flip.found` / `flip.verified` | `{"flip": Flip}` |
| `usage` | `UsageData` |
| `report.ready` | `{"report": Report}` |
| `run.finished` | `RunFinishedData` |
| `run.failed` | `RunFailedData` |

`borges.garden.executor.GardenExecutor` emits `checkpoint.created`, `universe.started` and
`universe.finished`. `borges.runs.orchestrator` emits everything else.

## 6. Demo (what the judges see)

1. **Landing.** A plain pitch sentence and a "Watch the 30-second demo" button above the
   fold, four case cards (checkout A/B test, red cards, MARP religiosity, MARP cultural
   norms) and a bring-your-own-data card that is disabled, with the reason, unless
   `/api/health` reports `uploads_available`. Unknown runs, cases and URLs show a not-found
   page with links home.
2. **Live garden.** A radial labyrinth grows from the dataset at the centre: one ring per
   step, one branch per option, every node a real sandbox checkpoint. Counters show
   universes, forks, tokens and dollars.
3. **The flip.** The verdict card turns from SHIP to DON'T SHIP, the smallest-flip path lights
   up, and the justification and its source appear.
4. **Step into the universe.** A drawer shows the exact code, row counts at each step, the
   result, the checkpoint ids, the judge score (or "planner option, not judged") and a
   reproduce command computed by the server at read time: `borges reproduce --case C
   --universe U` for recorded demos, `python borges_<run>_<u>.py --data <file>` plus a
   script download (`GET /api/runs/{run}/universes/{u}/script`) otherwise. `borges
   reproduce` re-executes the universe on the case data with the local backend and exits 1
   with `MISMATCH` unless estimate, interval, p-value, n and verdict equal the recording.
   A flip that did not reproduce is marked as unconfirmed.
5. **Specification curve.** Every universe's estimate with its CI against the decision
   threshold, axes labelled. Cases with a reference (red cards, both MARP cases) show the
   human teams' results in a lane. The verdict card shows the flip kind (direction or
   significance), the effect range over the explored universes and the search-bias caveat.
6. **Decision influence.** The decisions ranked by how much they move the answer.

## 7. Run modes

- `llm=scripted`: deterministic hand-built responses from `cases/<id>/fixtures/`, labelled
  `scripted`, 0 tokens, $0. Used by tests, CI and the offline demo.
- `llm=nebius`: live Nemotron through Token Factory, with cache and spend cap. Never run so
  far (no key). `make live-smoke` checks the ids and one call per role; `make record-live`
  records both curated cases under `BORGES_RUN_CAP_USD`.
- `backend=local`: a directory per checkpoint (copy-on-write clone where available) and a
  subprocess with timeout, resource limits, a scrubbed environment and the AST guard. It is
  not an isolation boundary (shared filesystem and network). Used for development, CI and
  scripted demos on a private or disposable machine.
- `backend=contree`: Nebius Token Factory Sandboxes. Each step is `image.run(...,
  disposable=False)` on the parent image. VM isolation; contract-tested with a fake SDK, and
  the live test skips without credentials and has never run.
- `replay`: re-stream a recorded run, with no models and no sandboxes.

The run header shows the mode of each run (`Scripted replay` or `Live on Nemotron`, plus the
backend), taken from `run.started`. The landing footer follows `/api/health`.

### Public deployment

There is no hosted demo yet. A public instance replays scripted runs (hand-built, not live
model runs) on the local backend, and should run live or upload workloads only on
`BORGES_BACKEND=contree`. The server, not the client, chooses the backend. `POST /api/runs` applies a policy: it clamps
`max_universes` to `BORGES_MAX_UNIVERSES`, answers 429 when `BORGES_MAX_ACTIVE_RUNS` runs are
active or `BORGES_MAX_LIVE_RUNS` live runs are active, and rejects live runs when there is
no key (400) or the spend cap is used up (403). `/api/health` reports
`llm_live_available` and `live_unavailable_reason` (`no_key` or `budget_spent`), and the
case cards disable the live button with that reason. It also reports `uploads_available` and
`uploads_unavailable_reason`, derived by `api/live_rules.py` with the same rules the policy
uses. Uploads (CSV or parquet) need live mode; the local backend refuses them (400) unless
`BORGES_ALLOW_UNTRUSTED_LOCAL=true`, and when `BORGES_LIVE_TOKEN` is set the header
`X-Borges-Live-Token` must match it (the built-in UI does not send it). Live runs on a
curated case are not refused on the local backend by the policy; that combination must not
be exposed publicly.

| Variable | Public instance |
|---|---|
| `BORGES_ALLOW_UNTRUSTED_LOCAL` | `false` (the image default). `make dev` and `make serve` set `true`. |
| `BORGES_BACKEND` | `contree` if uploads should run live; `local` otherwise. |
| `BORGES_LIVE_TOKEN` | Set it to gate uploads. |
| `BORGES_MAX_ACTIVE_RUNS`, `BORGES_MAX_LIVE_RUNS` | Concurrent run limits (defaults 2 and 2). |
| `CONTREE_PROJECT_ID` | ConTree project (falls back to `NEBIUS_PROJECT_ID`). |
| `/app/.borges` volume | Holds `spend.json` and the LLM cache; without a volume the spend ledger resets on every redeploy. |

CI (`.github/workflows/ci.yml`) runs ruff, pytest and the frontend typecheck, tests and
build on every push. `runs/` is not part of the image, so run ids vanish on redeploy; the UI says so when it
opens a run that no longer exists.

## 8. Exact formats shared by several domains

**`Option.code`** is complete Python source that defines exactly one function:
- `apply(df, ctx)` returning a DataFrame, for steps of kind `filter`, `transform` and
  `feature`;
- `estimate(df, ctx)` for the step of kind `model`, returning a dict with float keys
  `estimate`, `ci_low`, `ci_high`, `p_value`, an int `n`, and an optional
  `extra: dict[str, float]`.

Top-level `import`/`from` of allowed modules is permitted; any other top-level statement
is rejected by `code_guard`. `ctx` may be mutated in place (it is persisted as JSON after
every step). Functions must be deterministic: any randomness uses a fixed seed.

**Case folder** `cases/<case_id>/`:
- `case.json`: a `CaseSpec`;
- `data.parquet`: the dataset;
- `fixtures/`: the scripted model responses;
- `recorded/events.jsonl`: optional, a recorded run for offline replay;
- `live_only` in `case.json` (default false): a live-only case has no `fixtures/` and no
  recording, runs only with `llm=nebius`, and the registry refuses a scripted run with a clear
  message (`CaseRegistry.require_scripted`).

**Scripted fixtures.** A request `key` maps to the file `fixtures/<key with ":" replaced by
"__">.json`, holding `{"model": str, "text": str, "parsed": object|null, "tokens_in": int,
"tokens_out": int}`. Keys:
- `planner` (parsed = `PlannerOutput`);
- `coder:<step_id>.<option_id>` (parsed = `CoderOutput`);
- `coder:<step_id>.<option_id>:repair` (parsed = `CoderOutput`);
- `adversary` (parsed = `AdversaryOutput`);
- `judge:<step_id>.<option_id>` (parsed = `JudgeOutput`);
- `narrator` (parsed = `NarratorOutput`).

Hand-built fixtures carry `"model": "scripted"` (MARP: `scripted-fixture`) and 0 tokens;
scripted calls report `cost_usd = 0` and 0 tokens. A live run with
`record_dir` writes exactly this format, so any live run can be replayed deterministically
afterwards.
