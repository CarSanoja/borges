# BLADE benchmark evidence

Pending: the live benchmark has not been run yet. The lead runs it with
`make bench-blade-live BLADE_DIR=<clone of github.com/behavioral-data/BLADE>`; each run writes a
dated folder here with `summary.md`, `summary.json` and the BLADE-format submissions. See
`src/borges/bench/README.md` for the method and its differences from BLADE.

## Re-scoring a finished run

`borges bench blade-rescore --out evidence/blade/<date> --blade-dir <clone>` rebuilds every
analysis from `runs/`, rebuilds the exact matcher messages, and reads only
`matcher-cache/`. A reply missing from the cache is reported as `missing`, never as 0%, and the
mean F1 of a row with a missing kind is withheld. Results go to `<date>/rescore/`. With `--live`
the missing replies are asked of the model and cached; nothing is re-run.

A cached reply is keyed by the hash of the messages, so any change to a prompt or to the items
sent makes the old replies `missing` for that kind.

## 2026-10-03 live run: what the numbers meant

The runs that died on the network (`Connection error`) have no analyses and no scores; they are
listed under "Skipped" and must be re-run. Of the seven rows that completed, the zeros were not
measurements. Every `model` and `transform` reply in the cache was a bare `{}`, and so were the
`cvar` replies of affairs and teachingratings, although the lists plainly contained matches (for
example expert "negative binomial regression" against agent "negative binomial regression", or the
beauty score against its description). The prompts for those kinds had no worked example, unlike
BLADE's, and the matcher asked for json_object with thinking off. The replies also showed key
spellings the parser dropped ("1-A1B1", "B1-A2", "A3-A5-A6-B3"). The scores of
`rescore-as-run/` reproduce the published table from the cache and are kept only as the record of
what the degenerate replies produced.
