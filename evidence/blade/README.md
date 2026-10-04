# BLADE benchmark evidence

The live benchmark has run. `make bench-blade-live BLADE_DIR=<clone of github.com/behavioral-data/BLADE>`
writes a dated folder here with `summary.md`, `summary.json` and the BLADE-format submissions.
See `src/borges/bench/README.md` for the method and its differences from BLADE.

## 2026-10-04: the committed results

| File | Commit | Runs with analyses | Cost |
|---|---|---|---|
| `2026-10-04/summary.md` | `a5252e3` | 24 of 24 | $0.3582 |
| `2026-10-04/summary-36b2f77.md` | `36b2f77` | 22 of 24 (amtl failed in both arms) | $0.3470 |

Both tables score 12 datasets with two arms: planner only, and planner plus adversary. The
matcher is `nvidia/nemotron-3-super-120b-a12b`. Mean F1 over the 12 datasets in the `a5252e3`
table, computed from `summary.json`: planner 0.468, adversary 0.480. The adversary is at or above
the planner on 9 of 12 datasets: 5 of those are exact ties, it is higher on 4 (two by 0.005 or
less) and lower on 3.

Read these numbers with the limits in mind:

- There is one repeat per dataset. The two tables differ by as much as the arms do: affairs
  planner scores 0.55 in the `36b2f77` table and 0.31 in the `a5252e3` table. The arm difference
  (0.012) is smaller than that, and one repeat cannot show whether it is more than noise.
- Transforms are matched semantically by the matcher, not by BLADE's data-value hashes.
- BLADE's model-with-variables metric is not computed.
- Coverage of models and transforms is low on several datasets, and one run per dataset does
  not say which part is Borges and which is the matcher.
- No other tool was run on the same datasets, so there is no comparison with one.

The `36b2f77` amtl runs died because a spec asked for one level of a four-level text column
against the rest and the template accepted two levels. `a5252e3` fixed that.

## Re-scoring a finished run

`borges bench blade-rescore --out evidence/blade/<date> --blade-dir <clone>` rebuilds every
analysis from `runs/`, rebuilds the exact matcher messages, and reads only
`matcher-cache/`. A reply missing from the cache is reported as `missing`, never as 0%, and the
mean F1 of a row with a missing kind is withheld. Results go to `<date>/rescore/`. With `--live`
the missing replies are asked of the model and cached; nothing is re-run.

A cached reply is keyed by the hash of the messages, so any change to a prompt or to the items
sent makes the old replies `missing` for that kind.

## 2026-10-03 live run: why it is not kept

The 3 October run (commit `5cdcbe5`) is not in the repository. Seventeen of its 24 runs died on a
network error (`Connection error`) and have no analyses. Of the seven that completed, the zeros
were not measurements. Of the 21 matcher replies of those seven runs, 18 were a bare `{}`: all
14 `model` and `transform` replies and 4 `cvar` replies (affairs and teachingratings), although
the lists plainly contained matches (for example expert "negative binomial regression" against agent "negative binomial
regression"). The prompts for those kinds had no worked example, unlike BLADE's, and the matcher
asked for json_object with thinking off. The parser also dropped key spellings such as "1-A1B1",
"B1-A2" and "A3-A5-A6-B3". Both were fixed (`6c5217f`, `94fb417`) and the benchmark was run
again on 4 October.
