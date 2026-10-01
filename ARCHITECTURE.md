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
| `analysis` | The plan (steps, options, decision rule), the LLM roles that create and judge it, the harness that turns an option into executable code | `models.py`, `planner.py`, `coder.py`, `adversary.py`, `judge.py`, `narrator.py`, `code_guard.py`, `harness.py`, `profile.py` |
| `garden` | Universes, prefix-shared execution, minimal-flip search, influence, verification | `models.py`, `executor.py`, `search.py`, `influence.py`, `verify.py` |
| `sandbox` | Branchable execution backends behind one protocol | `backend.py`, `local_backend.py`, `contree_backend.py`, `factory.py` |
| `llm` | Role-based model routing, structured JSON output, disk cache, cost accounting, hard spend cap | `client.py`, `nebius_provider.py`, `scripted_provider.py`, `cache.py`, `spend.py`, `json_output.py`, `factory.py` |
| `runs` | Orchestration, event bus, run store, replay, state folding | `events.py`, `orchestrator.py`, `bus.py`, `store.py`, `replay.py`, `state.py` |
| `cases` | Curated demo cases (dataset + pinned plan + recorded model responses) | `registry.py`, plus `cases/<id>/` data folders |
| `api` | HTTP + SSE + static UI | `app.py`, `routes_*.py`, `schemas.py` |

## 3. The execution model (the core idea)

**Option code contract.** Each option is a Python function body. Non-final steps implement
`def apply(df, ctx) -> df`. The final step (`kind == "model"`) implements
`def estimate(df, ctx) -> dict` and returns `estimate, ci_low, ci_high, p_value, n`.
`ctx` is a JSON-serialisable dict that carries decisions forward (e.g. a covariate list
chosen at step 3 and read by the model at step 5). Allowed imports: pandas, numpy,
scipy(.stats), statsmodels(.api/.formula.api), math. `code_guard` enforces this with an AST
allowlist.

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
4. pair flips, ranked by how far each single change moved the estimate toward the
   threshold (only if no single flip was found, or the budget allows);
5. verification of the minimal flip: re-execution from the root with no prefix cache, and
   the result must match exactly.

**Minimal flip** = the flipped universe with the fewest changes. Ties go to the higher
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

The estimated live cost is about $0.02-0.05 per run. Money controls:
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

1. **Landing.** "29 teams. Same data. Opposite answers." There are two case cards (checkout
   A/B test, red cards) and an upload card.
2. **Live garden.** A radial labyrinth grows from the dataset at the centre: one ring per
   step, one branch per option, every node a real sandbox checkpoint. Counters show
   universes, forks, tokens and dollars.
3. **The flip.** The verdict card turns from SHIP to DON'T SHIP, the minimal-flip path lights
   up, and the justification and its source appear.
4. **Step into the universe.** A drawer shows the exact code, row counts at each step, the
   result, the checkpoint ids and "reproduced ✓".
5. **Specification curve.** Every universe's estimate with its CI against the decision
   threshold. On the red-cards case the 29 human teams are overlaid.
6. **Decision influence.** The decisions ranked by how much they move the answer.

## 7. Run modes

- `llm=scripted`: deterministic recorded responses from `cases/<id>/fixtures/`. Used by tests,
  CI and the offline demo.
- `llm=nebius`: live Nemotron through Token Factory, with cache and spend cap.
- `backend=local`: a directory per checkpoint (copy-on-write clone where available) and a
  subprocess with timeout. Used for development and CI.
- `backend=contree`: Nebius Token Factory Sandboxes. Each step is `image.run(...,
  disposable=False)` on the parent image.
- `replay`: re-stream a recorded run, with no models and no sandboxes.
