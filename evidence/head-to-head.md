# Borges against persona sampling and a fixed grid

Measured on 7 October 2026 (UTC), on the two real cases whose published answers Borges is not
told. Everything here ran live on Nemotron through Token Factory, except the fixed grid, which is
Steegen et al.'s hand-built multiverse recomputed offline.

## The three approaches

- **Borges**: the full pipeline (planner on Super, judge and narrator on Ultra, coder on
  Lightning, adversary, bounded search for the smallest flip).
- **Persona sampling**: `scripts/persona_baseline.py`, built for this comparison
  (`src/borges/evaluation/persona_baseline.py`). Twelve analysts, each the planner model with a
  persona in its system message ("an economist", "a methodologist who worries about small samples
  and flexible analyses", "a data scientist with no background in the field", ...). Each plans as
  Borges's planner does, but only its own default path is coded, by the same coder, code guard and
  smoke repair Borges uses, and executed through the same harness. Nothing forks, no judge scores
  options, no adversary proposes any and nothing searches for a flip. Raw output:
  `evidence/head-to-head/persona_*.json`.
- **Fixed grid**: Steegen, Tuerlinckx, Gelman and Vanpaemel (2016), 120 processing combinations
  of the fertility data chosen by four methodologists, recomputed by
  `cases/fertility_religiosity/steegen_multiverse.py`. No published grid exists for the teaching
  data.

## Fertility and religiosity, from the question alone

| | Borges, 15 completed live runs | Persona sampling, 12 analysts | Steegen's grid, 120 |
|---|---|---|---|
| Verdicts | 15 NO CLEAR EVIDENCE | 9 NO CLEAR EVIDENCE, 3 failed to run | p < .05 in 7 of 120 |
| How the cycle day is counted | 13 forward from the last period, 2 from cycle length alone | 9 forward from the last period | all 120 back from the next expected period, as the published study does |
| Results inside Steegen's grid | 0 | 0 | 120 |
| Significant results | none that stand (three reported flips did not, `evidence/repeats.md`) | none (smallest p .068) | 7 of 120, the published analysis among them |
| Cost | $0.03 to $0.07 a run | $0.120 for the twelve (125 calls) | no model calls |

From the question alone, neither automated approach reaches the region where the published effect
is significant. Both count the cycle day the way the data's column names suggest, forward from the
last period, and neither proposes the convention the published study used. Their null verdicts
agree with Steegen's conclusion that the effect is fragile, but they do not show it: they never
run an analysis on which it holds.

## Fertility and religiosity, from the published analysis (`fertility_published`)

The case gives Borges the analysis behind the published result, as Steegen et al. reconstructed
it, and asks how fragile it is. The analysis stays the starting point (the judge may dispute it,
which the report states, but cannot replace it) and a second model checks that the plan's default
path implements it before anything runs.

| | Borges, run 1 (`r_20261007T033617_784e1b`, local) | Borges, run 2 (`r_20261007T035352_3cba38`, ConTree) | Steegen's grid |
|---|---|---|---|
| Starting point | 2.3834, p .012, n 163 | 2.3834, p .012, n 163 | 2.3834, p .012, n 163 |
| Smallest flip | 1 change: single = not dating, committed = engaged or married, dating women left out (proposed by the adversary) | 1 change: committed = married only (proposed by the planner) | 6 of the 9 single changes lose p < .05 |
| Flipped result | NO CLEAR EVIDENCE, 1.7793 [-0.4812, 4.0398], p .1218, n 129 | NO CLEAR EVIDENCE, 0.8642 [-1.1754, 2.9037], p .4039, n 163 | R2 p .384, R3 p .122, NMO2 p .836, F3 p .099, F5 p .257, EC2 p .066 |
| Checked by | Steegen's R3 cell, computed independently: 1.7793, p .1218, n 129 | refit from the raw data: 0.8642 [-1.1754, 2.9037], p .4039, n 163 | `steegen_multiverse.py` |
| Cost | $0.084 | $0.080 | no model calls |

In both runs Borges found a single defensible change that removes the effect, both times in how
relationship status is coded, which is the decision Steegen et al. also found most influential
(R2 and R3 both lose significance). It did not propose the other forks of their grid that flip the
result (the reported instead of the computed cycle length, other fertility windows, excluding
women unsure of their dates), so it finds a smallest flip, not the whole fragile region.

Persona sampling has no column here: its analysts do not start from an analysis, and none of the
twelve reproduced the published one.

Two attempts to record this case failed before measuring anything and led to fixes, and one was
discarded: the planner transcribed "single = 1 or 2" as single = 1 and called it the user's
definition, and the judge accepted it. That run measured the fragility of an analysis nobody
brought, which is why the fidelity check exists (`src/borges/analysis/planner_fidelity.py`). In
the recorded run the check caught the religiosity mean counting unanswered items as 0, and the
planner fixed it before coding.

## Teaching ratings

| | Borges, live recording | Persona sampling, 12 analysts |
|---|---|---|
| Verdict | BEAUTY PREMIUM, no flip in 20 universes (9 of 9 live runs without a flip) | 12 of 12 BEAUTY PREMIUM |
| Distinct analyses | 18 distinct results among 20 universes | 2 distinct results among 12 analysts (0.1565 and 0.1645) |
| Range of estimates | 0.1226 to 0.1693 | 0.1565 to 0.1645 |
| Cost | $0.050 | $0.043 |

On a robust effect both agree. Twelve personas produce two analyses: a different persona does not
make a different analysis, which is the weakness of persona sampling as a way to explore
defensible choices.

## Limits

- One persona run of twelve analysts per case; two Borges runs from the published analysis. These
  are rates from small numbers.
- The persona baseline uses Borges's own planner model and coder, so it measures what the forking
  search adds over independent analysts with the same models, not over other tools.
  `agentic-forking-path` was not run.
- The fixed grid for fertility is the published one, designed by experts after the original
  paper; nothing automatic produced it.

## Reproduce

```bash
uv run --no-sync python cases/fertility_religiosity/steegen_multiverse.py
uv run --no-sync python scripts/persona_baseline.py --case fertility_religiosity --n 12 --out /tmp/p.json
uv run --no-sync borges replay --case fertility_published
```

The persona script needs `NEBIUS_API_KEY`; the other two make no model call.
