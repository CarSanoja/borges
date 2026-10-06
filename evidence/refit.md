# Independent refit of every live headline

On 5 October 2026 every headline number in the six final live recordings was refitted by an
auditor that did not read Borges's code: five Sonnet 5.5 agents, reading the final recordings and
the raw data, with no live model or sandbox calls. For each case the auditor took the baseline universe (all
defaults) and the minimal-flip universe; when there was no flip, it took the finished universe
farthest from the baseline. It implemented each universe from the option specs in the plan, in
plain pandas and statsmodels, without reading the recorded option code. Only when the numbers
disagreed did it read the code, and then it classified the gap. Agreement means a relative
difference below 1e-6 on the estimate and both interval bounds, with the same n.

The scripts are in `evidence/refit/`. Run them from the repository root, for example
`uv run python evidence/refit/red_cards.py`. Each prints its numbers next to the recorded ones.
Where a spec allowed two readings, the MARP and hurricanes scripts print both.

## Headline numbers

| Case | Universe | Recorded | Refit | Largest relative difference | n |
|---|---|---|---|---|---|
| checkout_ab | baseline `u_e929526ea4` | 0.8495 pp [0.1516, 1.5473], p 0.0170 | same | 5.5e-14 | 16000 |
| checkout_ab | flip `u_fb948f9bb7` | -0.1492 pp [-0.7987, 0.5004], p 0.653 | same | 2.4e-14 | 15829 |
| red_cards | baseline `u_e493e6469a` | OR 1.1702 [1.0497, 1.3047], p 0.0046 | same | 6.8e-14 | 124621 |
| red_cards | flip `u_0c4e209321` | OR 1.1230 [0.9812, 1.2854], p 0.0922 | same | 1.1e-14 | 61822 |
| marp_religiosity | baseline `u_abc552de6d` | 0.093128 [0.075745, 0.110511] | same, with the outcome standardised | 1.2e-8 | 10170 |
| marp_religiosity | farthest `u_2b28306b3a` (median regression) | 0.054781 [0.041064, 0.068497] | 0.054729 [0.041011, 0.068447] | 1.3e-3 | 10170 |
| marp_norms | baseline `u_52d4b71a62` | 0.035180 [0.018245, 0.052116] | same, with the outcome standardised | 1.1e-7 | 10503 |
| marp_norms | farthest `u_23b24e6d08` | 0.048313 [0.020888, 0.075738] | same, with the outcome standardised after the complete-case drop | 3.6e-8 | 10503 |
| bank_marketing_calls | baseline `u_df834e741d` | OR 0.87165 [0.85731, 0.88623], p 3.07e-59 | same | 3.0e-15 | 45211 |
| bank_marketing_calls | farthest `u_c20f30a6a4` | OR 0.90329 [0.88810, 0.91874] | same | 4.8e-16 | 45211 |
| hurricanes | baseline `u_b4716afa30` | 0.010662 on log1p(deaths) [-0.072662, 0.093986], p 0.802 | same | 2.3e-14 | 93 |

Every baseline and every flip agrees. The one gap is a universe off the headline: the
adversary's median regression in marp_religiosity, at 1.3e-3. The auditor put it down to the
iterative solver on a design with a nearly collinear country and GDP block (finding 4 below). Two
readings needed the recorded convention to match:

- **MARP.** The decision rule's metric is a standardised coefficient. The recorded code z-scores
  the outcome as well as the exposure; the spec says only "standardised". Read literally, with
  the outcome raw, the estimates are smaller by the outcome's standard deviation (0.61): 0.0568
  and 0.0214, with the same p-values and n. The auditor called the z-scored reading the more
  defensible one.
- **red_cards.** The spec says exp(b ± 1.96·SE); the recording uses statsmodels' 1.959964. The
  bounds differ by 2e-6 with 1.96 and by 7e-14 with the exact quantile.

## Findings that are not headline numbers

The refit also checked universes off the headline. What it found:

1. **bank, before `80d3ae6`: a headline weighted by its own exposure.** The first final bank
   recording (at `5070877`) reported OR 0.9067 [0.9013, 0.9122], p 2.5e-225. The planner's
   spec said "weighted logistic regression" and named no weight. Borges refuses code that drops
   the weights an option asks for, so the coder weighted each client by `campaign`, the exposure
   itself, as frequency weights. Unweighted, the same model gives 0.8773 [0.8613, 0.8935],
   p 2.3e-44. The verdict was the same, but the interval was about three times too narrow. The
   harness now fails a model whose weights equal the exposure column (`80d3ae6`, test
   `tests/analysis/test_harness_exposure_weights.py`). Of the ten distinct recorded model codes
   that weight, only this one weights by the exposure. bank was recorded again at `6317040`, and
   that recording is the one above.
2. **hurricanes: the Poisson option ignores the transform step.** Its spec models `outcome` (the
   square root or asinh of deaths) unless the outcome is log-transformed. The code fits raw
   deaths in every case, so the sqrt, asinh and log1p Poisson universes give the same number.
   The report already counts identical results once ("18 universes ran but only 12 gave
   distinct results"), so the robustness share is not inflated. Fitting raw counts is the sounder
   Poisson model, but it is not what the spec says.
3. **hurricanes: the universes are on two scales.** OLS universes are on log1p, sqrt or asinh
   deaths; Poisson universes report an average marginal effect in deaths (about 3 deaths per unit
   of `masfem`, delta-method interval). A literal reading of the Poisson spec, (IRR - 1) × mean
   deaths with an exponentiated interval, gives 3.19 [0.14, 6.61], p 0.040, where the recording
   gives 3.00 [-0.49, 6.50], p 0.092. The recorded estimator is the standard one. Verdicts
   compare signs and p-values, which do not depend on the scale, and the report states the
   headline's log scale. The "farthest from baseline" universe is chosen across scales, though,
   so it is not a meaningful distance here.
4. **marp_religiosity: the adversary's median regression is on the raw outcome scale.** The OLS
   options z-score the outcome; the adversary's quantile regression does not. Its universes
   (0.045 to 0.056) look smaller than the baseline (0.093). On the standardised scale they are
   0.073 to 0.092. All are positive and significant, so no verdict changes. The same universe
   is the one cross-platform reproduce mismatch (4e-6, `evidence/live-runs.md`).
5. **red_cards: an unrelated citation on the flip.** The judge attached
   `https://doi.org/10.1186/s12974-020-01855-9`, a neuroinflammation paper, to the "at least 2
   games together" option. Citations come from the models and nothing checks them. The CLI and
   the web app now label them "cited by the model, not checked" and no longer link them
   (`43d913c`).
6. **Smaller notes.** checkout's adversary option "exclude sessions over 3600 s" removes no rows
   (the report names it as a no-op and leaves it out of the robustness share and the flip
   search). bank's clustered standard errors use 12 job
   clusters with no small-sample correction, which is likely anti-conservative. Only
   non-headline universes use them.
