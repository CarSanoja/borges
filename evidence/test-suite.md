# Test suite

The full suite ran green on 6 October 2026. The logs are committed in `evidence/test-suite/`.

| What | Commit | Result | Log |
|---|---|---|---|
| `ruff check`, `ruff format --check` on `src` and `tests` | `43d913c` | clean | `pytest-43d913c.log` |
| `pytest` (the default `-m 'not live'`) | `43d913c` | 3,302 passed, 7 skipped, 2 deselected, 0 failed, in 32 min | `pytest-43d913c.log` |
| Frontend typecheck, `vitest`, production build | `b5c9510` | clean; 296 tests in 66 files passed; build exit 0 | `frontend-b5c9510.log` |
| The 64 Python tests that read the live recordings or the README | final state | 64 passed | `recordings-final.log` |

`43d913c` is the last commit that changes Python code. The commits after it change the
recordings, the evidence, the documentation and the frontend, so the 64 tests that read the
recordings or quote the README were run again on the final state. The frontend was run at
`b5c9510`.

The 7 skipped tests need things this Mac does not have: Linux rlimits (`test_limits.py`, two),
`resource.prlimit` and `/proc` (two sandbox policy tests), a BLADE clone (two), and a run
directory outside the checkout (one). The 2 deselected tests are marked `live`: they call Token
Factory and ConTree, and they run only when enabled. The ConTree live test passed against the
real service on 2 October (`evidence/live-runs.md`).

To run the same checks:

```bash
uv run --no-sync ruff check src tests && uv run --no-sync ruff format --check src tests
uv run --no-sync pytest -q -rs
pnpm -C frontend exec tsc --noEmit -p tsconfig.app.json && pnpm -C frontend exec vitest run && pnpm -C frontend build
```
