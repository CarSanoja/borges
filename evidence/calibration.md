# Calibration of the bounded flip search

Question (jury item K9): is the bounded flip search biased toward finding flips? Offline study, scripted mode, nothing live: no model and no ConTree were called, and there is no NEBIUS_API_KEY on the machine.

## What was run

504 synthetic checkout datasets with the schema of `cases/checkout_ab` (about 30,000 sessions each), generated with `cases/checkout_ab/generate.py` parameters (`true_effect`, `novelty_bump`, `internal_user_share`, `n_users`; defaults reproduce the committed `data.parquet` byte for byte, tested). Each one went through the real Borges pipeline (planner, baseline, single flips, adversary round, combinations, fresh-sandbox verification) with `--llm scripted` and the local backend. The coder fixtures are code that the sandbox executes on each dataset, so every estimate and p-value is computed from that dataset; the planner and the adversary proposals and judgements are replayed, so the menu of 5 decision steps and 1 accepted adversary option is the same for every dataset.

- True lift grid (conversion probability, absolute): null 0, 0.0037 (about 50% power for the default analysis), 0.0053 (80%), 0.0069 (95%), 0.0100 (about 99%). Powers were checked by simulation on 150 clean datasets each: 3%, 51%, 78%, 94%, 99% SHIP. Novelty bump is 0 in all cells, so the true effect is the only real effect.
- Artefact: absent (`clean`, no internal users) or present (`artefact`, 1.15% of users, 80% in treatment, 58% conversion, as in the case).
- Seeds: `20261002 + cell_index * 1,000,000 + i`. The `ship` stratum scans seeds in order and keeps only datasets where the default analysis says SHIP (3,164 null clean datasets scanned to get 80 false SHIPs; P(SHIP | null, clean) = 80/3164 = 2.5%, which is the nominal rate).
- Flip kind: `direction` if the flipped estimate has the opposite sign of the baseline, otherwise `significance` (same sign, p crosses 0.05, like the flagship OR 1.34 to 1.20 flip).
- Intervals are Wilson 95%. Cells have 80 replicates (headline) or 24 or 40 (secondary, intervals up to about +-20 points: treat as indicative).

## Results

"Flip" = Borges reports a flip (any verdict change found within the budget). k/n, rate, 95% interval.

| Effect | Artefact | n | Default analysis says SHIP | Any flip reported | Direction flip | Flip via internal traffic |
|---|---|---|---|---|---|---|
| null | clean | 40 | 0/40 | 3/40, 8% [3, 20] | 0/40, 0% [0, 9] | 0/40 |
| null, false SHIP only | clean | 80 | 80/80 | **71/80, 89% [80, 94]** | 0/80, 0% [0, 5] | 1/80 |
| 50% power | clean | 24 | 6/24 | 6/24, 25% [12, 45] | 0/24 | 0/24 |
| 80% power | clean | 24 | 16/24 | 11/24, 46% [28, 65] | 0/24 | 0/24 |
| 95% power | clean | 24 | 21/24 | 13/24, 54% [35, 72] | 0/24 | 0/24 |
| large | clean | 80 | 80/80 | **13/80, 16% [10, 26]** | 0/80, 0% [0, 5] | 0/80 |
| null | artefact | 80 | 77/80 | 78/80, 98% [91, 99] | 35/80, 44% [33, 55] | **76/80, 95% [88, 98]** |
| 50% power | artefact | 24 | 24/24 | 22/24, 92% [74, 98] | 1/24 | 22/24, 92% [74, 98] |
| 80% power | artefact | 80 | 80/80 | 55/80, 69% [58, 78] | 0/80, 0% [0, 5] | **55/80, 69% [58, 78]** |
| 95% power | artefact | 24 | 24/24 | 16/24, 67% [47, 82] | 1/24 | 16/24, 67% [47, 82] |
| large | artefact | 24 | 24/24 | 5/24, 21% [9, 40] | 0/24 | 5/24, 21% [9, 40] |

Headline numbers:

- False alarms, large true effect and no artefact: a flip was reported in 13/80 = 16% (95% interval 10 to 26%). All 13 were significance crossings with the same sign; none was a direction flip.
- Flip from a false SHIP (null effect, no artefact, default analysis says SHIP): a flip was reported in 71/80 = 89% (80 to 94%). None was a direction flip (0/80, upper bound 5%); 71 of 71 were significance crossings.
- Detection of the planted artefact (null effect): the flip excluded internal traffic in 76/80 = 95% (88 to 98%), and 35/80 = 44% (33 to 55%) of these were direction flips. With a true effect at 80% power the flip went through the internal-traffic filter in 55/80 = 69% (58 to 78%); at a large effect, 5/24 = 21% (9 to 40%, secondary cell).
- Direction flips on clean data: 0 of 272 datasets across all clean cells with a SHIP-capable effect or null (upper 95% bound about 1.4%).

## What this means, including the uncomfortable parts

1. The search is biased toward finding flips, and the bias is in the significance kind. When the default analysis wrongly says SHIP on a null effect, the search almost always (89%) finds some defensible alternative whose p-value crosses 0.05. A reported flip of the significance kind is therefore weak evidence that the original verdict was fragile because of a real problem: it is expected from noise near the threshold. Even with a large, real effect, 16% of runs report one.
2. Direction flips are specific. In 272 clean datasets there was no direction flip; in the artefact null they occur in 44%. The product should lead with the kind: "the sign reverses" is a strong claim, "p crosses 0.05" is not. The flagship flip of the checkout case (OR 1.34 to 1.20, estimate still above 1) is of the weak kind. The case itself has a planted artefact; on this study's artefact cells the internal-traffic step is found 95% of the time when the true effect is null, which supports the mechanism, not the size of the claim.
3. Detection falls as the true effect grows (95%, 69%, 21%): a real effect survives dropping the internal sessions, so no flip is found there, which is the right behaviour, but it also means "no flip" does not prove the absence of the artefact.
4. Limits: the plan is fixed (5 steps, 2 options each, one scripted adversary option), so rates apply to this menu, not to any dataset; the effect grid has no novelty bump, bots only as in the generator, and the secondary cells are small. The default analysis ignores clustering by user, which is part of why SHIP is not conservative here.
5. The run took about 38 minutes of wall time (5 worker processes on a heavily loaded Mac, 3.3 hours of summed per-run time), a little over the 30 minutes planned.

## Reproduce

```
uv run --no-sync python scripts/calibrate_flips.py --workers 5 --out evidence/calibration.json --rows /tmp/calibration.rows.jsonl
uv run --no-sync python scripts/calibrate_flips.py --smoke --out /tmp/smoke.json
uv run --no-sync pytest -q tests/evaluation
```

The first command rebuilds the same datasets from the seeds above (resumable through the rows file; re-running with `evidence/calibration.rows.jsonl` as `--rows` only recomputes the summary). Per-dataset rows are in `evidence/calibration.json` and `evidence/calibration.rows.jsonl`.
