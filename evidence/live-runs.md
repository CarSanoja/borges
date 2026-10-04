# Live runs on Nemotron through Nebius Token Factory

State at HEAD, 4 October 2026 (UTC). The six committed recordings were made on 4 October from an
empty model cache, on Token Factory models and ConTree sandboxes, at commit `36b2f77`. Later
commits changed the coder's model-spec validation (`a5252e3`) and added documents and evidence;
they did not change a recording. The recordings of 2 October and the first ones of 3 October were
replaced and are not kept. The 2 October failure table below is kept as history.

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

| Case | Run | Calls (cached) | Tokens in / out | Cost | Universes (failed) |
|---|---|---|---|---|---|
| checkout_ab | r_20261004T021145_b35c59 | 29 (0) | 59,721 / 9,841 | $0.0244 | 10 (0) |
| red_cards | r_20261004T021401_f056a7 | 40 (0) | 77,546 / 8,581 | $0.0297 | 7 (0) |
| marp_religiosity | r_20261004T021652_9b9a83 | 23 (0) | 74,622 / 4,802 | $0.0225 | 10 (0) |
| marp_norms | r_20261004T021841_a241e4 | 39 (0) | 131,782 / 9,665 | $0.0408 | 29 (0) |
| bank_marketing_calls | r_20261004T022158_acad7c | 32 (0) | 63,783 / 7,797 | $0.0233 | 7 (0) |
| hurricanes | r_20261004T023159_0d9d8d | 33 (0) | 59,226 / 5,578 | $0.0253 | 17 (0) |

| Case | Original verdict | Smallest flip found | Reproduce |
|---|---|---|---|
| checkout_ab | SHIP: 0.5277 pp [0.107, 0.9484], p 0.014, n 29926 | Exclude internal sessions only: -0.1398 [-0.493, 0.2135], p 0.438, n 29587, DON'T SHIP (direction). Not marked contaminated | baseline u_d081a4f779 MATCH, flip u_2daf3a388e MATCH |
| red_cards | NO CLEAR EVIDENCE: OR 1.134 [0.9493, 1.354], p 0.166, n 123868 | Negative binomial regression with robust SE: OR 1.254 [1.05, 1.498], p 0.0126, n 123868, BIAS DETECTED (significance) | baseline u_5da228aed5 MATCH, flip u_b11428d86a MATCH |
| marp_religiosity | POSITIVE ASSOCIATION: 0.06064 [0.05006, 0.07122], p 2.76e-29, n 10503 | none | u_7e77454495 MATCH, u_8228635c7e MATCH |
| marp_norms | DEPENDS ON NORMS: 0.02137 [0.0111, 0.03164], p 4.55e-05, n 10503 | none | u_77372ba4e4 MATCH, u_6b8631b9bb MATCH |
| bank_marketing_calls | CAP THE CALLS: OR 0.8694 [0.8552, 0.8839], p 7.02e-62, n 45211 | none | u_4497380b21 MATCH, u_f695e88066 MATCH |
| hurricanes | FEMININE NAMES DEADLIER: 1.098 [1.082, 1.114], p 1.14e-35, n 93 | Adjust for elapsed years plus Quasi-Poisson regression: 1.056 [0.9793, 1.14], p 0.156, n 92, NO CLEAR EVIDENCE (significance; labelled an estimand change) | baseline u_490c1df0e1 MATCH, flip u_1f1eec7c9f MATCH |

The lead ran the reproduce column: 12 of 12 MATCH. For the four cases without a flip, the two ids
are the baseline and the last universe. The reproduce results are the lead's; this document did
not re-run them.

Design-weighted robustness share in the recordings (`report.robustness`), with the universes
explored: checkout_ab 0.5 (10), red_cards 0.33 (7), marp_religiosity 1.0 (10), marp_norms 1.0
(29), bank_marketing_calls 1.0 (7), hurricanes 0.8 (17). The report rates a share only with
enough distinct results; only marp_norms (1.0) and hurricanes (0.8) have a rating, the others
say "too few to rate". For bank, the design note says one decision changed at a time and
interactions between decisions are not covered.

## What the recordings show

- **checkout_ab.** The data is synthetic (`cases/checkout_ab/generate.py`). The baseline is now
  the naive default: keep all sessions, SHIP. The smallest flip excludes internal sessions and
  gives DON'T SHIP. The recording's flip has `contaminated: false`: it is no longer the
  direction the r6 jury criticised, where a plan that already excluded invalid rows flipped by
  re-including them. The column notes still say internal sessions are not genuine customers, so
  the model had that hint. The replication with the notes stripped is not done.
- **One re-plan.** The checkout run made one live `step.replanned` event. The model step lost
  both options (`model_ols_clustered`, `model_glm_robust`) and the planner replaced them with
  `model_linear_platform_day`, `model_logit_robust_se` and `model_wls_platform_day`.
- **red_cards.** The baseline is NO CLEAR EVIDENCE (OR 1.134, p 0.166). The smallest flip is
  significance only, under a negative binomial model with robust SE. The 29 teams of Silberzahn
  et al. (2018) reported ORs between 0.89 and 2.93. Seven universes is a narrow space; the
  report does not rate the share.
- **hurricanes.** The flip changes two decisions (elapsed years as a covariate, Quasi-Poisson)
  and the recording labels it an estimand change: it adds a covariate, so it answers a
  different question.
- **bank_marketing_calls.** No flip in 7 universes. The significance-only flip of 2 October
  (listwise deletion, robust SE) that the r6 jury disputed is not in the recording.
- **MARP.** No flip in 10 universes (religiosity) and 29 (norms).
- No universe failed in any of the six.
- One run per case is one sample of a model. It is not a measure of how often Nemotron finds a
  flip, and it is not a comparison with another tool.

## BLADE benchmark

`evidence/blade/2026-10-04/summary.md` (commit `a5252e3`, 24 of 24 runs with analyses, $0.3582)
and `summary-36b2f77.md` (commit `36b2f77`, 22 of 24; both amtl runs failed, $0.3470) score
Borges against the expert decisions of BLADE on 12 datasets, planner arm and adversary arm. Mean
F1 over the 12 datasets, computed from `summary.json`: planner 0.468, adversary 0.480. There is
one repeat per dataset, and the two tables differ by as much as the arms do (affairs planner 0.55
in the first, 0.31 in the second). The arm difference is within noise. Transforms are matched
semantically by the matcher, not by BLADE's data-value hashes, and BLADE's model-with-variables
metric is not computed. See `evidence/blade/README.md`.

## ConTree against the real service

All six recordings above ran on ConTree. Earlier checks on 2 October 2026:

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
