# Borges frontend

React 19 + TypeScript (strict) + Vite single page app for the garden of forking paths demo.

## Develop

```
pnpm install
pnpm dev
```

The dev server starts on http://localhost:5173. Without a backend, use mock mode (below).

## Test

```
pnpm test --run
pnpm typecheck
```

`src/App.test.tsx` plays the whole mock run through `App` with fake timers and asserts the garden, verdict flip, specification curve and universe drawer.

## Build

```
pnpm build
pnpm preview
```

## Mock mode

Append `?mock=1` to any run route to replay the bundled sample run (fixtures in `src/fixtures`) with no backend:

```
http://localhost:5173/run/sample?mock=1
```

The landing page also exposes it through its sample action. Events are replayed with their original pacing, capped at 650 ms per step, so the full run takes about a minute.

## Routes

- `/` landing with the case cards
- `/run/:runId` live run over server-sent events
- `/replay/:caseId` recorded run
- add `?mock=1` to either run route to use the fixture

## Layout

Code is organised by feature in `src/features` (garden, verdict, speccurve, influence, telemetry, universe, cases, run). Shared contracts, API client and router live in `src/shared`; `src/shared/types/contracts.ts` mirrors the backend and is never edited here.
