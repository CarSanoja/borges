# Live runs on Nemotron through Nebius Token Factory

Nine recordings are committed: six made on 5 October 2026 (UTC), described first, and three made
on 7 October with the judge and narrator on Ultra (see the two "7 October" sections below). The role table that
follows is the 5 October one.

State at `43d913c`, 5 October 2026 (UTC). The six committed recordings were made on 5 October from
an empty model cache, on Token Factory models and ConTree sandboxes: four at `16f02e7`, red_cards
at `5070877` and bank_marketing_calls at `6317040`. Between `16f02e7` and `43d913c` the code
changed in four places: re-plans drop options the judge rejected (`05d0306`), the fleet seed
imports in one pass (`e295b8f`), a model may not weight rows by its own exposure (`80d3ae6`), and
model-written citations are labelled as unchecked (`43d913c`). None of the four `16f02e7`
recordings made a re-plan or weights by the exposure, so none of these changes touches them.
red_cards was recorded again because its `16f02e7` recording took a rejected option as its
baseline through a re-plan. bank was recorded again because the independent refit
(`evidence/refit.md`) found its `5070877` headline weighted by the exposure. The 4 October
recordings were replaced. The defects each round of recordings exposed are in
`evidence/census.md`.

| Role | Model |
|---|---|
| Planner, adversary, judge, repairer, reviewer | `nvidia/nemotron-3-super-120b-a12b` |
| Coder | `nvidia/Nemotron-3_5-Lightning` |
| Narrator | `nvidia/Nemotron-3-Ultra-550b-a55b` |

The coder changed from `nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B` after a measured comparison
(`evidence/coder-choice.md`). Nano and Super stay allowed through `BORGES_CODER_MODEL`. They are
alternatives that an operator picks, never fallbacks. The defaults are in `DEFAULT_ROLE_MODELS`
(`src/borges/llm/client.py`) and `policy/gateway.json`; each recording's `run.started` event lists
the models it used.

Each recording is `cases/<case>/recorded-live/{events,spans,audit}.jsonl` plus `recording.json`
(run id, commit, `dirty: false`, backend `contree`, cost, verdicts). The web app plays
`events.jsonl` by default. `borges reproduce --case <case> --universe <id> --source live`
re-executes a recorded universe from scratch and must match the recording exactly.

## The six recordings

| Case | Run | Commit | Calls (cached) | Tokens in / out | Cost | Universes (failed) |
|---|---|---|---|---|---|---|
| checkout_ab | r_20261005T224722_45a899 | `16f02e7` | 41 (0) | 84,125 / 8,316 | $0.0291 | 16 (0) |
| red_cards | r_20261005T233430_dece7c | `5070877` | 41 (0) | 91,006 / 9,408 | $0.0306 | 22 (0) |
| marp_religiosity | r_20261005T225939_5d10af | `16f02e7` | 31 (0) | 109,730 / 7,543 | $0.0352 | 12 (0) |
| marp_norms | r_20261005T230329_f634c9 | `16f02e7` | 53 (2) | 193,230 / 15,222 | $0.0564 | 29 (8) |
| bank_marketing_calls | r_20261005T234748_d4616e | `6317040` | 33 (0) | 72,311 / 7,390 | $0.0257 | 12 (0) |
| hurricanes | r_20261005T231651_d38583 | `16f02e7` | 39 (0) | 85,268 / 7,994 | $0.0304 | 18 (0) |

Calls are the `llm_calls` of each recording's last `usage` event, $0.2073 for the six. The model
cache was empty when each batch started. The two cached calls in marp_norms are the same runtime
repair of `opt_pca_cnorm` asked twice inside that run (`borges.cache.hit` in `spans.jsonl`).
marp_norms has 8 failed universes. Six of them are every universe with the PCA cultural-norms
scale, whose step was stopped. The report says that decision was not tested.

| Case | Original verdict | Smallest flip found | Reproduce |
|---|---|---|---|
| checkout_ab | SHIP: 0.8495 pp [0.1516, 1.547], p 0.017, n 16000 users | Exclude internal sessions: -0.1492 [-0.7987, 0.5004], p 0.653, n 15829, DON'T SHIP (direction). Not marked contaminated | baseline u_e929526ea4 MATCH, flip u_fb948f9bb7 MATCH |
| red_cards | BIAS DETECTED: OR 1.17 [1.05, 1.305], p 0.0046, n 124621 | Keep dyads with at least 2 games together plus skin-tone threshold at 0.5: OR 1.123 [0.9812, 1.285], p 0.0922, n 61822, NO CLEAR EVIDENCE (significance) | baseline u_e493e6469a MATCH, flip u_0c4e209321 MATCH |
| marp_religiosity | POSITIVE ASSOCIATION: 0.09313 [0.07574, 0.1105], p 8.61e-26, n 10170 | none | u_abc552de6d MATCH, u_0e615ae60a MISMATCH at the 7th digit (below) |
| marp_norms | DEPENDS ON NORMS: 0.03518 [0.01825, 0.05212], p 4.67e-05, n 10503 | none | u_52d4b71a62 MATCH, u_23b24e6d08 MATCH |
| bank_marketing_calls | CAP THE CALLS: OR 0.8716 [0.8573, 0.8862] per call, p 3.07e-59, n 45211 | none | u_df834e741d MATCH, u_c20f30a6a4 MATCH |
| hurricanes | NO CLEAR EVIDENCE: 0.01066 on log1p(deaths) [-0.07266, 0.09399], p 0.802, n 93 | none | u_b4716afa30 MATCH, u_6ac18fdb4b MATCH |

The reproduce column was run on 5 October on the local backend, at `5070877` and, for bank, at
`6317040`. For the cases
without a flip, the second id is the finished universe farthest from the baseline, measured on
the raw estimate when these runs were reproduced. That distance mixes scales (log deaths against
deaths), so `scripts/live_runs_table.py` now picks it by the largest change in z = (estimate -
decision threshold) / standard error and prints that measure under the table; its ids differ
for three of the four cases without a flip and the ids above were not reproduced again. 11 of 12
MATCH. The twelfth is the adversary's median quantile regression in marp_religiosity. On macOS
it gives 0.04461034 [0.03156106, 0.05765961]; the recording, on ConTree's Linux, gave
0.04461015 [0.03156089, 0.05765941]. The relative difference is 4e-6, the p-value, n and verdict
are equal, and the cause is the iterative solver of `QuantReg`. Reproduction is exact for the
closed-form and IRLS fits, and within 1e-5 for the quantile regression across platforms.
Every baseline and flip was also refitted by an auditor that did not read the code, from the
specs and the raw data (`evidence/refit.md`). All agree to 2e-7 or better.

Design-weighted robustness share in the recordings (`report.robustness`), with the universes
explored: checkout_ab 0.56 (16), red_cards 0.70 (22), marp_religiosity 1.0 (12), marp_norms 1.0
(29), bank_marketing_calls 1.0 (12), hurricanes 1.0 (18). Each share comes from a uniform random
sample of the analysis grid, independent of the beam search. The report states the sample size
and the number of distinct results with the share.

## 7 October: two published answers that Borges is not told

`fertility_religiosity` (Durante et al. 2013, and the multiverse of Steegen et al. 2016) and
`teaching_ratings` (Hamermesh and Parker 2005) are live-only cases: no scripted fixtures, and the
published answer is in each case's README, not in anything Borges reads. Models from 6 October:
planner Super with Ultra as fallback, judge and narrator Ultra, coder Lightning, adversary,
repairer and reviewer Super. The judge moved to Ultra (agent version 2.0.0). The planner went back
to Super after five fresh Ultra plans of the fertility case were all unusable: four had no model
step and wrote options as pandas code, one was cut at 8,192 tokens. Super gave five usable plans
out of five.

| Case | Run | Commit | Calls (cached) | Tokens in / out | Cost | Universes (failed) |
|---|---|---|---|---|---|---|
| fertility_religiosity | r_20261007T020642_a23fe3 | `14adc35` | 50 (1) | 118,066 / 10,751 | $0.0674 | 32 (0) |
| teaching_ratings | r_20261007T013204_6521d3 | `0859f2c` | 39 (0) | 84,647 / 10,607 | $0.0497 | 20 (0) |

| Case | Original verdict | Smallest flip found | Reproduce |
|---|---|---|---|
| fertility_religiosity | NO CLEAR EVIDENCE: 0.2746 [-2.053, 2.602], p 0.817, n 171 | none | baseline u_311ac33ed6 MATCH, farthest u_1b2af9882d MATCH |
| teaching_ratings | BEAUTY PREMIUM: 0.1645 [0.1034, 0.2257], p 1.33e-07, n 463 | none | baseline u_6cefe77c73 MATCH, farthest u_0c7221cc4f MATCH |

Reproduced on 7 October on the local backend, at `aff311c`. The refit is in `evidence/refit.md`:
both baselines and the teaching farthest universe agree to 2e-14; the fertility farthest universe
has the right estimate and a wrong interval, explained there.

- **teaching_ratings.** 0.1645 is Hamermesh and Parker's adjusted specification on these data
  (0.165 with the same covariates), and the farthest universe, with no covariates and errors
  clustered by instructor, is their simple one: 0.1330 [0.0252, 0.2408], p 0.0156, against the
  published 0.133 [0.025, 0.241]. No defensible flip in 20 universes, as a sound tool should find.
  All nine live runs of 6 and 7 October said BEAUTY PREMIUM and none found a flip
  (`evidence/repeats.md`).
- **fertility_religiosity.** Durante et al. report the interaction at p = .012; Steegen et al.
  found p < .05 in 7 of 120 defensible processing choices and called the effect too fragile to be
  taken seriously. Borges says NO CLEAR EVIDENCE with no flip in 32 universes. That is not a
  reproduction of the multiverse: the plan's window is 6 to 11 days since the last period, not
  Durante's cycle days 7 to 14 counted back from the next onset, and none of the plans of the 15 completed
  runs counted back (13 counted forward, 2 used cycle length alone), so no Borges universe lies in Steegen's grid and none reached its 7
  significant cells. The judge
  rejected the plan's default of keeping every participant (0.3), so the original analysis
  excludes women with a date certainty of 5 or less on either date (n 171), and the report says
  so; with everyone kept the verdict is the same (-0.2646, p 0.777, n 275). All fifteen completed live
  runs of 6 and 7 October said NO CLEAR EVIDENCE, one of them on a result its code invented
  (`evidence/repeats.md`).

Two fertility recordings were made and discarded before this one:

1. **The wrong coefficient.** `r_20261007T013144_46bc17` reported 0.1688 [-0.0416, 0.3793],
   p 0.116 as the interaction. A refit gave 0.3621 [-1.8165, 2.5407], p 0.745: the recorded
   number was the coefficient of Sure2, the last covariate. The spec model had named indicators
   that exist only inside the model step, so the template was skipped, and the repaired free code
   read `params.iloc[-1]`. Fixed at `c0ec1c3`: model code that reads an estimate by position is
   refused (50 of 373 free model codes in the live caches of that day did; no shipped fixture or
   recording does), and an indicator of a column built by an earlier step is resolved to that
   column and level, so the template renders. Replayed offline with the same plan and spec, the
   template gives 0.36213, the refit.
2. **The wrong construct.** `r_20261007T014606_9884cb` coded its plan correctly, but the plan's
   high-fertility group was fewer days since the last period than a third of the cycle: days 0 to
   9, which include menstruation. The judge accepted it (0.6).

The planner sets a fertility window against its published meaning in about one run in four on this
case: 2 of 8 live runs and 3 of 12 fresh plans after the question was clarified. Three defences
were measured on labelled options and none was adopted: a judge instruction on constructs
rejected 0 of 5 wrong windows; with reasoning on, 2 of 5 at three to four times the cost; a
dedicated construct auditor caught 8 to 9 of 11 but called 12 to 13 of 25 correct windows
invalid. Every construction rule is listed in the plan view, and that is where a person has to
look. Each recording above was checked by refit before it was kept.

## 7 October: starting from the published analysis

`fertility_published` gives Borges the analysis behind the published fertility result and asks
how fragile it is (`cases/fertility_published/README.md`). The recording is
`r_20261007T035352_3cba38` on ConTree, $0.080, 59 calls: it starts from the published 2.3834,
p .012, n 163 and its smallest flip is one change, committed = married only, which gives 0.8642
[-1.1754, 2.9037], p .4039, n 163. A refit from the raw data and `borges reproduce --source live`
both give the same numbers. Its `recording.json` names `3e1d0c9`, the commit when the recording
was copied; the run loaded its code at `7b6bb27`, and between the two only the registry seed, the
persona baseline and two web-app merges changed, none of which a run uses.

Seven attempts were made, all listed in `evidence/repeats.md`. Three measured the published
analysis and all three found a one-change flip in the relationship coding; the other four led to the fixes that
the recorded run uses: the user's analysis is a field of its own that the judge cannot replace, a
per-row quantity may not be kept in ctx in prose or as a mask, and a fidelity check compares the
plan's defaults with the analysis before anything runs.

## What the recordings show

- **checkout_ab.** The data is synthetic (`cases/checkout_ab/generate.py`). The plan aggregates
  sessions to users (16,000), keeps all sessions by default and says SHIP. Excluding the 171
  internal sessions gives DON'T SHIP. That is the planted answer, reached through a model-written
  plan. The column notes say internal sessions are not genuine customers, so the model had that
  hint. The blind-notes repeats (`evidence/repeats.md`) measure how often it finds the exclusion
  without them.
- **red_cards.** The plan asks whether a player in the darker half of the skin-tone ratings has
  higher odds of any red card. BIAS DETECTED with OR 1.17. The smallest flip needs two changes
  (dyads with at least 2 games together, the 0.5 threshold) and crosses p = 0.05 only. The 29
  teams of Silberzahn et al. (2018) reported ORs between 0.89 and 2.93, median 1.31.
- **hurricanes.** The planner's only filter excludes the top 1% of deaths, which drops the
  deadliest storm (1,833 deaths; 94 storms become 93) from every universe. No universe shows feminine names deadlier. That is the
  outlier critique of the original study, and it is one plan's choice; the repeats show how often
  the planner makes it.
- **bank_marketing_calls.** No flip in 12 universes. OR 0.872 per extra call, unweighted. The
  `5070877` recording had reported 0.907 from a model that weighted each client by the number of
  calls; the refit caught it (`evidence/refit.md`).
- **MARP.** No flip in 12 universes (religiosity) and 29 (norms).
- One run per case is one sample of a model. The repeats in `evidence/repeats.md` measure how
  stable the verdict and the flip are across runs.

## An uploaded dataset, end to end

On 6 October 2026 (00:10 UTC) the server at `b5c9510` (ConTree backend, registry enforced) took
a CSV it had never seen: the public teaching-ratings data (463 course evaluations, 13 columns,
from the BLADE benchmark). The question was "Do instructors rated as more beautiful get higher
teaching evaluations?", with BEAUTY PREMIUM if the change in evaluation score per unit of beauty
is above 0 at p < 0.05.

- As anonymous demo access, the upload card says before submitting that an upload needs an API
  key with `uploads:write`, and the button is disabled. The server refuses the upload with the
  same reason.
- With a 12-hour local key holding that scope, `POST /api/uploads` profiled the file (no personal
  data found) and `POST /api/runs` started a live run, `r_20261006T001048_abd03c`.
- It completed in 148 s: BEAUTY PREMIUM, 0.141 [0.076, 0.206], p 2.3e-5, n 463, 18 universes,
  none failed, no flip, robustness 100% on a 12-draw grid sample. 23 calls, $0.0162. Hamermesh and
  Parker (2005) report a coefficient of about 0.13 on these data.
- The key was revoked afterwards. The run is not committed as a recording.

## BLADE benchmark

`evidence/blade/2026-10-04/summary.md` (commit `a5252e3`, 24 of 24 runs with analyses, $0.3582)
and `summary-36b2f77.md` (commit `36b2f77`, 22 of 24; both amtl runs failed, $0.3470) score
Borges against the expert decisions of BLADE on 12 datasets, planner arm and adversary arm. Mean
F1 over the 12 datasets, computed from `summary.json`: planner 0.468, adversary 0.480. There is
one repeat per dataset, and the two tables differ by as much as the arms do (affairs planner 0.55
in the `36b2f77` table, 0.31 in the `a5252e3` table). The arm difference is smaller than that,
and one repeat cannot show whether it is more than noise. Transforms are matched
semantically by the matcher, not by BLADE's data-value hashes, and BLADE's model-with-variables
metric is not computed. See `evidence/blade/README.md`.

## ConTree against the real service

All six recordings above ran on ConTree (`backend: contree` in each `recording.json`). Earlier checks on 2 October 2026:

| Check | Result |
|---|---|
| `tests/sandbox/test_contree_live.py` | passed in 41.8 s |
| checkout_ab, scripted, `BORGES_BACKEND=contree` (r_20261002T155240_392c19) | 7 universes, 22 real ConTree checkpoints, the same flip as the local backend (SHIP to DON'T SHIP) |
| marp_religiosity, live on Nemotron plus ConTree (r_20261002T155440_0aa541) | completed, 16 universes, 31 checkpoints, no flip, $0.0069 recorded (25 of 30 calls came from the model cache) |
| marp_religiosity, live on Nemotron plus ConTree with an empty model cache (r_20261003T190856_374165, 3 October) | completed, 16 universes, 31 ConTree checkpoints, no flip; 23 model calls, 0 from cache, 69,603 / 5,169 tokens, $0.0196; `borges audit verify` OK on 152 audit records |

## 3 and 4 October: live failures and fixes

The ledger gives a run id for few of these. Where it does not, the cell says so. Each fix has a
test.

| Live failure (run) | Fix | Commit |
|---|---|---|
| checkout: the guard rejected patsy coefficient labels such as `params["C(variant)[T.treatment]"]` and the repairer repeated the error. The run died after 24 s (no run id in the ledger) | Coefficient labels pass the guard. An indexed formula term gets a hint on how to write it | 26d9c50 |
| red_cards: two serial model steps, and the coder read `ctx['skin_tone']`. marp_norms: the repairer returned unterminated code with no other option coded (no run ids) | One final model step. A fresh re-code after a failed guard repair | 0d990e6 |
| marp_norms: the coder read `ctx['outcome']` five times. bank: a one-option one-hot step whose `produces` did not match (no run ids) | Columns are read from `df`, not `ctx`. The repairer is hinted. Dummy encoding stays inside the model step | 11f2317 |
| BLADE live run died when the matcher returned invalid JSON; a network cut at 22:29 UTC on 3 October killed 17 of 24 runs with `Connection error` (no run ids) | The matcher retries once and reports unmatched chunks instead of aborting. The network cut was not fixed in code; a longer retry policy was tried and reverted | 5cdcbe5 |
| The model step passed its smoke run at the first try in 13% of 212 options and 37% still failed after repairs (`evidence/coder-choice.md`) | The model step is rendered from a structured spec by tested templates, tried before free code. A skipped template records why | 1ca6a2e, 2908cbe, 8c23ccc |
| checkout: the planner's spec asked for estimates times 100, the reviewer marked the correct template unfaithful, and the scale check killed the re-code (no run id) | HC0 and HC2 templates. The unit contract overrides the spec. Reviewer points that only demand a unit conversion are dropped | 7d6d73a, ca867a2 |
| checkout: Armor read Borges's own repair hint ("drop incomplete rows; this filters") as an instruction to ignore rules (no run id) | Composed prompts and generated code are screened with unambiguous override verbs only. User input keeps the broad rule | 7d6d73a |
| red_cards: the planner proposed dummy fixed effects for every player and referee, a design of 1,577 columns, rank-deficient (no run id) | Specs with dummy fixed effects on identifiers with hundreds of levels are refused (cardinality rule); the planner is told to cluster instead | 6f5798b |
| A step that lost every option killed the run | One re-plan by the planner. A re-plan drops options that repeat a failed spec; ctx covariates come from code first | 3f09228, 11be5ab |
| red_cards (confirmation round 4): the template reported `games`, the offset column, as the exposure; the judge had rejected the alternatives; the run ended with 1 universe and the UI said "No defensible flip found" | The offset is never the exposure. An invalid spec gets one corrective retry | 37e2456 |
| The same run: a run where only the default analysis ran could claim the decision held | Such a run says robustness was not tested ("Not tested: only the default analysis ran") | 57a8a60 |
| Re-recording at `273a4ff`: checkout had 12 failed universes (a text `variant` column fell to free code) and 5 of 6 reports repeated deterministic caveats | Text exposure levels and a logit average marginal effect in the templates. Each caveat is reported once. `marginal_effect` needs an unscaled 0/1 exposure | 5feb939, fc6f2bb, 36b2f77 |
| BLADE at `36b2f77`: both amtl runs died. The spec asked for `genus == 'Homo sapiens'`, one level against the rest of 4 levels, and the template accepted only 2 levels | A listed level of a text exposure with up to 12 levels is coded against all the others | a5252e3 |
| Tests: `test_value` expected 11 coder calls and the template requests made it 14; a lease test reclaimed an expired lease inside the polling window | The expected count is 14. The other owner holds a live lease in the test | 6232c7c, 997cf6f |
| BLADE: matcher replies were `{}` for model and transform items, so scores were 0% | BLADE-style prompts with worked examples, a second look on empty replies, letter-based pair parsing and an offline re-score from cached replies | 6c5217f, 94fb417 |

The coder default changed in `8895e4a`, with `BORGES_CODER_MODEL` added in `201d92b`.

## 5 October: live failures and fixes

The rounds of 5 October are described in full in `evidence/census.md`. The table lists those
found while the final recordings were made.

| Live failure (run) | Fix | Commit |
|---|---|---|
| bank (rec38): a flip to NO CASE FOR A CAP from a Bayesian logit whose repaired code returned the coefficient 0 and variance 1 when the fit failed, and a p-value computed as a share of draws | Fixed numbers or an identity covariance assigned in a branch that tests isfinite/isnan/isinf or in an except clause are refused unless the branch raises, and so is a p-value computed as the mean of a comparison | 072aac4 |
| red_cards (fin10): `term.startswith('C(')` and `"y ~ x + "` read as unfinished formulas; every model option and the re-plan were refused | Constants used as startswith/endswith/in probes, or that end in an operator, are not parsed as formulas | e62ed6d |
| checkout (rec40): "group by user_id" coded as if apply() saw one user, returning one row; the model was blamed | A transform that says "group by X" and returns fewer rows must return one row per value of X | 70292e4 |
| red_cards (rec41): a re-plan brought back an option the judge had rejected, and it became the baseline (BIAS DETECTED, OR 1.37) | Re-planned options the judge already rejected are dropped | 05d0306 |
| Runtime queue tests timed out under load: the fleet seed imported one event at a time and re-verified the chain each time | One verification and one write for the whole import | e295b8f |
| bank (rec41, found by the independent refit): the default model weighted each client by `campaign`, the exposure, as frequency weights (OR 0.9067, interval three times too narrow) | A model whose weights equal the exposure column fails the step | 80d3ae6 |
| red_cards (rec42, found by the refit): the judge's citation for the flip's games filter is a neuroinflammation DOI | Model citations are labelled "cited by the model, not checked" and no longer linked | 43d913c |

## 2 October: live failures and fixes (history)

These are the failures of the first live day. The recordings made then are no longer in the
repository.

| Live failure (run) | Fix | Commit |
|---|---|---|
| checkout: lift -0.14 pp with 95% CI [-0.145, -0.138] and p = 0. The standard error was about 50 times too small (r_20261002T111336_e14c7c) | The smoke test re-estimates on random halves of the data and rejects intervals far too narrow | eef02fc |
| checkout: CI [-341, +341] percentage points (r_20261002T120441_278425) | The same check rejects intervals hundreds of times too wide | c3f8ba6 |
| marp_norms: a "flip" to an estimate of -398,439 from a broken Bayesian option (r_20261002T111426_37181c) | Implausible estimates are failed universes, never flips | 1b3fc97 |
| marp_religiosity: option ids with a leading space; a stray closing brace in repaired code (r_20261002T111520_be5792) | Ids are normalised; a trailing closer line is removed when that makes the code parse | 1b3fc97, eef02fc |
| marp_religiosity and bank: KeyError on columns that earlier steps never created (r_20261002T112912_2f1dd7, r_20261002T112942_0c8cf0) | Steps declare the names they produce. The harness enforces them and lists the available columns on a KeyError | 5a98479, 70cf108, bbe5a7e |
| checkout: an "exclude none" filter that dropped every control row; a "control indicator" option that only flips the sign (r_20261002T112723_77b03c) | Smoke runs report observed effects. A deterministic orientation check fails reversed columns. Nemotron Super reviews every option's code against its spec and the observed effects | 70cf108, 9e0c719 |
| marp_norms: a mirror flip (+0.037 to -0.037, same rows) from an unoriented PCA score (r_20261002T112828_6a407b) | Orientation check and coder rule. Report caveat for mirror flips | 9e0c719, bbe5a7e |
| checkout: aggregating sessions to users dropped the treatment column (r_20261002T115928_477b3a) | After an aggregation, columns constant within each group are carried along | 0560840 |
| red_cards: missing skin-tone ratings broke the model fit (r_20261002T115327_abc043) | Model steps start from complete cases. Fit errors list missing values per column | 909261e |
| bank: "Firth's penalized logistic regression" was a plain Logit with an unseeded bootstrap. The run did not reproduce (r_20261002T115529_c4bc7a) | Step randomness is seeded. The planner names only estimators that statsmodels or scipy provide. The reviewer checks that the named estimator is the one fitted. Adversary options are reviewed too | de16fb3 |
| bank: coefficient on the log-odds scale (-0.116) judged against "odds ratio < 1". No universe could ever flip (r_20261002T121458_92f1ee) | A ratio rule requires positive estimates and intervals. The coder is told the rule's scale | 2a71bd9 |
| marp_norms: the minimal flip used cnorm_2 - cnorm_1, a planner alternative whose own rationale said both items are positive indicators (r_20261002T130325_2d3cd2) | Every planner alternative passes the same defensibility judge as adversary proposals, with the column notes, before it is coded | 7696862, 9d792e0 |
| red_cards and bank: a default model that failed its smoke run killed the whole run (r_20261002T133928_9088c0, r_20261002T133954_258ab5) | One fresh re-code by Super, then promotion of a passing alternative with a caveat; error hints for statsmodels distributions and covariate lists | 60131bc |
| marp_norms: the coder filtered attention-check failures inside the model step, so the filter step was a no-op and the report said filtering had no influence (r_20261002T133635_b00f08) | Model steps may only drop incomplete rows; a static guard rejects value filters and sends them to repair | 7193bd3, 3aa99a8 |
| marp_religiosity: the judge rejected an alternative proposed by the planner and accepted the same one from the adversary (r_20261002T133753_a5365d) | Adversary duplicates reuse the planner's judgement | 7193bd3, 3aa99a8 |
| marp_religiosity and marp_norms: a prompt rule for percentage points was applied to standardised coefficients (12.78) (r_20261002T143403_7c310e) | Units are decided in code from the case metric; the model returns its natural scale | 90a791c |
| checkout: the narrative named a different filter option than the one the flip changed (r_20261002T143218_a09f47) | The flip sentence is built in code and must appear verbatim; sentences naming another option of that step are removed | 90a791c, 3947452 |
| marp_norms: a PCA score reversed on the full data in a universe that did not flip (r_20261002T143306_67e104) | The reversal check runs on every universe | 9cd2822 |
| red_cards: a model with many dummies was singular on the 2,000-row smoke sample only (r_20261002T143018_92b96a) | Singular or separated fits are retried on up to 20,000 rows before counting as failures | 9cd2822 |


## Cost on 2 October

The development day made 45 live runs, 31 of which completed. Their recorded cost was $0.65. The spend ledger (`.borges/spend.json`) also counts the smoke checks: $0.76 over 1,096 calls. Every run that was not committed was rejected after a hand review, and the reasons are in the table above or in the commits that fixed them.

A complete live run of one case costs between $0.015 and $0.033.

A live run of one case in the six recordings above costs between $0.0225 and $0.0408 (table above). No total cost of 3 and 4 October is given here: it was not summed from a file.
