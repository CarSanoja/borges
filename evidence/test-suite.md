# Test suite

The full suite ran green on 9 October 2026, on the Mac, at the last commit that changes Python
code. The logs are committed in `evidence/test-suite/`.

| What | Commit | Result | Log |
|---|---|---|---|
| `ruff check`, `ruff format --check` on `src`, `tests`, `cases` and `scripts` | `978d42c` | clean | — |
| `pytest` (the default `-m 'not live'`) | `978d42c` | 3,921 passed, 7 skipped, 2 deselected, 0 failed, in 47 min | `pytest-978d42c.log` |
| Frontend typecheck, `vitest`, production build | `978d42c` | clean; 358 tests in 78 files passed; build exit 0 | `frontend-978d42c.log` |

The suite also ran green at `04ee11e` (3,915 passed). It includes the tests that read the live
recordings and quote the README.

The 7 skipped tests need things this Mac does not have: Linux rlimits (`test_limits.py`, two),
`resource.prlimit` and `/proc` (two sandbox policy tests), a BLADE clone (two), and a run
directory outside the checkout (one). The 2 deselected tests are marked `live`: they call Token
Factory and ConTree, and they run only when enabled. The ConTree live test passed against the
real service on 2 October (`evidence/live-runs.md`).

To run the same checks:

```bash
uv run --no-sync ruff check src tests cases scripts && uv run --no-sync ruff format --check src tests cases scripts
uv run --no-sync pytest -q -rs
pnpm -C frontend exec tsc --noEmit -p tsconfig.app.json && pnpm -C frontend exec vitest run && pnpm -C frontend build
```
