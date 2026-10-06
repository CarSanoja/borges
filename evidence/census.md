# Failure census

Every batch of live runs is a census: each run that did not complete, and each completed run
whose garden or report looked wrong, was read from its JSON, its events and its LLM cache, traced
to a root cause, and fixed with a test before the next batch. A batch is six recordings
(`borges record-demo`) and 35 repeats (`borges run --json`, five per case, the checkout case also
blind), each from an empty LLM cache and an empty Borges home, on Nemotron through Nebius Token
Factory with ConTree sandboxes.

| Commit | Runs completed | Root causes found | Fixed in |
|---|---|---|---|
| `fc858b9` | 33 of 35 | The planner wrote a produced ctx key as `ctx\|covariates`; the harness refused exact aliasing of year and elapsed years instead of dropping the redundant column as R's `lm` does. | `2386467`, `3c02c68` |
| `aab722e` | 34 of 35 | A re-planned model rebuilt a score from the raw items; a template reported the wrong exposure ("contact call" read as the column `contact`); default covariates rebuilt the exposure; a re-plan offered a column an aggregation had dropped. | `0194998`, `53cbc3b`, `4290274`, `608ad9b` |
| `608ad9b` | 31 of 35 | A re-planned model ignored `ctx['covariates']`; computed column keys on the data frame were refused; the products rule disabled the logit template; country fixed effects aliased a country-level covariate. | `6118a95`, `9180bc7`, `3cf355b`, `a24c76d` |
| `6118a95` | 33 of 35 | Armor read a computed `ctx['estimate'] = coefficient` as steering; a ctx entry held a label instead of its column name; the model probe blamed an upstream filter that empties the sample; an adversary option was never probed under the model; a vague narrator retry replaced a precise first draft; a difference rule accepted a ratio-scale estimate. | `0937242`, `90d0476`, `1dc2650`, `6517c69`, `636c3e2`, `a5802d9`, `5e7dace` |
| `d187b02` | 24 of 25, stopped early | Identifier columns (1,585 players, 3,147 referees) in a covariate list made the design singular (the failed run). In completed runs: the in-garden repair rewrote an option other universes had already run with; a per-user aggregate looked different on the smoke sample; the judge rejected every alternative of several steps and left a two-universe garden; a template spec named a derived 0/1 exposure or the offset as the exposure and fell back to free code; a log1p outcome was read as "additional deaths". | `e3bcc7e`, `ae44923`, `b438cd1`, `05e52c3`, `44e3d39`, `480a815`, `47f3ff3`, `101f690` |
| `2721f49` | 33 of 35 | A one-hot step dropped the original columns and a column with one level on the smoke sample gave no dummies (bank); the covariate step's default aggregated to one row per user and every model option, re-plan included, read session-level columns (checkout). In completed runs: models reading `ctx['outcome']` and GEE options fell back to free code; Armor refused coder output as dynamic code; the judge was denied for quoting a covariate list; the narrator could read the agreeing share as the reversing share; the design check described GEE's internal WLS; a log outcome was compared with a raw one; a games-weighted logit silently ignored its weights (found by the independent refit). | `3a340f9`, `a06a7a6`, `b2e3314`, `6722621`, `b98df06`, `7eb8bdf`, `e14c1f9`, `09df22c`, `7a24c36`, `d5415c3`, `89eae7b`, `bcc5f68`, `38dfb4c` |
| `88040a6` | 31 of 35 | A numpy median of a column with missing values gave a NaN threshold and a constant exposure, and the re-plan failed before the earlier step's other options were tried (red_cards); a step that formats the model's output was placed after the model (red_cards); the ctx guard refused covariate lists and did not swap a standardised outcome (marp_religiosity); the products guard asked a model to read a winsorised column none of its options used (checkout blind). In completed runs: ConTree operation timeouts were not retried and one replaced the baseline default on the full data (bank, marp_norms); an outcome choice written in prose ("Write 'x' to ctx['outcome']") was not seen, so the model ignored it (marp_norms); an unoriented principal component flipped sign between the sample and the full data and its universes were excluded as reversed (marp_norms). | `7e528d0`, `715c289`, `60a7a33`, `4b68f49`, `36e0670` |
| `efe1aa5` | 32 of 35 | The planner promised one column per level of an identifier (`user_id_17`) and the covariate step ran out of memory (checkout blind); an exposure marked as the one of interest was outranked by a list of independent variables and the template was refused (bank); a duplicated `job_missing` design column broke the model (bank). In completed runs: the options of an outcome transform built differently named columns, so the decision had no effect (hurricanes); a repair reversed a principal component's direction (marp_religiosity); a derived variable named differently was reported as a change of covariates; the cluster choice was split into ctx by an earlier step; a template spec dropped the covariates its option named (red_cards); an adversary covariate was probed only under the model's default, and a free-code option failed on it (checkout); `np.log1p` of negative balances left NaN and -inf and lost 9 of 14 universes (bank); the products guard refused a Poisson template on the raw count (hurricanes). | `ce3c2bc`, `d6d6140`, `a1b5133`, `bf2dc9d`, `30bfa3b`, `81c65dc`, `70d80d3`, `0708398`, `ee23905`, `32e050d`, `baef34e`, `83a8878` |
| `cecf187` | 35 of 35 | No run failed. In completed runs: an option written as "Same regression as OLS-HC3" was not expanded and its template dropped every covariate (marp_norms); an option that says it uses no covariates was made to read the covariate list, and a Firth option was fitted by plain maximum likelihood (bank, checkout blind); an adversary filter left a column all missing and an unguarded mode lost 4 universes (bank); the gateway read a prose label listing columns as a table header and denied the judge (marp_religiosity); a repair passed a link class to statsmodels; narrator caveats restated the search method. | `441b72d`, `8ae0623`, `483e1ef`, `e95ba73`, `e20e0fb`, `5b7869e` |
| `16f02e7`, red_cards `5070877`, bank `6317040` (final) | 34 of 35 | The failed red_cards run: its model option said "weighted" without naming a weight, the guard refused the unweighted code, and the re-plan's code was stopped by Armor (`__import__` read as dynamic code). In the recordings of the same round: a re-plan that brought back a rejected option (red_cards) and a model weighted by its own exposure (bank), both below | `05d0306`, `80d3ae6`; the vague "weighted" spec is open |

The d187b02 batch was stopped after 25 runs because the causes it had found were already fixed;
the next batch ran in full at the fixed commit.

The raw run files of the last three batches are in `evidence/repeats/` (`efe1aa5.tar.gz`,
`cecf187.tar.gz`, `final-2026-10-05.tar.gz`); `evidence/repeats.md` is generated from the final
batch and `evidence/adversary-ablation.md` from all three.

## After the last batch

The six committed recordings were then made at the final commit (`evidence/live-runs.md`). Reading
them found three more causes, fixed with tests before the recordings were made again: the planner
prompt both asked model options to name their covariates and an adjustment step to choose them, so
"OLS adjusted for platform and day" read an empty covariate list (checkout); the adversary, told
that its proposals repeated the plan, returned nothing (both MARP cases); the narrator told another
universe as the original analysis and credited an adversary that had added no option (marp_norms).
From the cecf187 batch itself: an array-API model that never dropped incomplete rows lost two
covariate options (hurricanes). Fixed in `ddbac77` (planner), `0e68ecd` (adversary retry),
`fa16861` (narrator) and `616f648` (complete cases); the fleet seed was published once more
(`9fbd2e3`) and the recordings were made again at that commit.

Reading the `9fbd2e3` recordings found four more: the narrator copied the rules around a
sentence it was told to quote into 27 of the 35 cecf187 summaries (found by replaying their cache)
and kept a caveat about re-execution when no flip was found; a Poisson option asked for
additional deaths computed them from the exponentiated intercept (an estimate of 1e45) because
count models reported only a rate ratio; an alternative that failed its smoke run disappeared
without a note. Fixed in `9c25a70`, `43adc84`, `784299a` (average marginal effect of a count
model with a delta-method interval, matching statsmodels to 1e-6) and `688a661`. The first
recording at `f6b1ee7` showed the narrator retrying a good first draft only because it phrased
the original estimate in its own words, and the retry was poorer; the narrator now retries only
for errors and adds a missing required sentence itself (`a67072d`, replayed offline on the 35
cecf187 first drafts: no false alarm).

The `2a2d925` recordings found two more. The model options were coded at the same time as the
steps before them, so the check that a model reads what an earlier step stores in ctx saw only
those steps' specs, and a spec in prose names no value: a template that ignored the outcome
choice passed, and the outcome decision had no effect (marp_norms). Fixed by coding model options
after the others (`b89daa7`). In bank, a model option asked for the coefficient of `campaign_w`,
a column the default of the earlier step does not build; the model spec then reported the
coefficient of `contact`, while the clustered option reported `campaign`, so the original verdict
came from the wrong exposure (odds ratio 1.30 against 0.89) and the "flip" was a change of
exposure. A spec is now refused when its exposure is not the column the dataset notes mark as the
exposure of interest, or not the column the option names, a suffixed name no step builds counting
as its source column (`d46c024`). The seed was published at `4323c97` and the six recordings
were made again at that commit.

The `4323c97` recordings confirmed both fixes (the outcome choice now moves the marp_norms
estimate and gives its flip; every bank universe reports `campaign`) and found three more. The
default bank model was free code that one-hot encoded the whole frame and then kept the columns
named in `ctx['covariates']`; the categorical covariates had become `job_admin.` and so on, so the
default analysis ran unadjusted while the report said it adjusted for six covariates. The harness
now fails a model step when a covariate the earlier step lists, with more than one value, is in no
term of the fitted model and not in the step's note (`9b825a3`); replayed on the recorded
universes, it marks the 10 bank universes of that option and none of the other five cases. The
narrator rule against naming another option of the flipped step marked true sentences about that
option's own result, and the retry kept only the required sentences (marp_norms); it now applies
to sentences about the flip only (`edda188`, retries on the 35 cecf187 first drafts down from 6 to
2, both real). A summary repeated the robustness headline with the beam-search caveat, and three
cecf187 summaries described the beam search, one wrongly; such sentences are dropped (`a8ca74b`).

The six recordings at `b4e2f4e` were read the same way. In the checkout case
two single-change flips both re-included rows the plan marks invalid; the report named the first,
and the summary called it the only flip and described the second as an accepted alternative.
Every contaminated flip is now reported (`af75806`). In red_cards the planner cut the skin tone
inside the model (`dark = 1 if skin_tone >= 0.5`); the template read the cut as the exact level
0.5, and a repaired free-code option counted a missing skin tone as light (n 146,028 against
124,621); the flip between them was labelled a change of covariates. The templates now take a
threshold exposure and drop missing values before the cut, refuse an exact level of a fractional
column, and a flip whose reported coefficient belongs to another quantity is labelled an estimand
change (`35335ce`). In the bank case a winsorising option and an adversary cap wrote copies
(`campaign_w`, `campaign_capped`) that no later step reads, so both were no-ops in every universe;
the planner and the adversary are now asked to change the column in place. In hurricanes the
headline flip changed the outcome scale and the caveat said so, but the summary did not; the
required flip sentence now carries the estimand change (`eee7b36`).

An independent refit of the `b4e2f4e` recordings (three offline auditors who implemented each
headline universe from its spec before reading the recorded code) agreed with checkout,
marp_religiosity, marp_norms and hurricanes once spec readings were aligned, confirmed the
red_cards and bank defects above, and found one more: a "Huber-White" logit was translated into
standard errors clustered on the exposure itself. A spec that clusters on a variable of the model
is now refused (`17615bc`). The recordings at `597c38e` showed the red_cards defect again in a
data step: `(rater1.fillna(0) + rater2.fillna(0)) / 2` gave 21,407 unrated dyads a skin tone of 0,
and the flip was the filter that removed them. A data step now fails when a new column takes one
value on every row where all the columns it reads are missing, or when a 0/1 cut codes the
missing rows of its column as one group, unless the option says it imputes (`1fa82aa`). Replayed
offline, the check marks nothing in the 18 recorded gardens besides that step, and 8 of 786
option runs in four earlier batches of repeats, all red_cards cuts that had coded unrated players
as light-skinned (6 of 20 red_cards repeats). The same recordings showed a flip that swapped the
outcome for a subscale reported as a re-analysis (marp_norms, now labelled, `91c5ad3`), a
template that reported additional deaths as its rule asks lost to a reviewer who wanted the IRR
its spec named (hurricanes, `a3fb2f8`), and narrator caveats that restated the method or came out
garbled; every caveat is now computed from the garden, and the narrator writes only the summary
(`e7cdadf`).

Two more rounds of six recordings followed. At `2327203` red_cards did not complete: a principal
component computed with `np.cov` over missing ratings came out as the constant 0 in every row, and
the model and its re-plan could only fail. A new column that is 0 on every row while the columns
it reads vary now fails the data step, and every missing-value error names the line that keeps
those rows missing (`e340584`). The same round showed a summary that copied a prompt instruction
and repeated sentences (`89ec534`), and a Poisson option in free code lost to a reviewer asking
for a ratio under a difference rule (`2c1c540`). At `8520d7a` all six completed, but the red_cards
headline came from a Poisson model in free code that built `dark_skin = skin_tone >= 0.5` inside
`estimate()` and fitted 146,028 rows where 124,621 had a rating. A model step that compares a
column with a value now fails when it reports more rows than that column has known values
(`78d9ed7`); replayed offline over every universe of the two previous rounds, with each model
re-executed, it marks nothing else, and in this round it marks exactly the two contaminated
universes. The same round lost six hurricanes universes to count models fitted on damage figures
up to 75,000 (a singular Hessian; rescaling the covariates leaves the exposure's coefficient
unchanged and the fit converges), lost a checkout option whose formula left out the exposure when
there were no covariates (the error now names the fitted terms), and leaked internal option ids in
a caveat (`0d6b0dc`, `63c765f`, `ea2a803`).

At `a0fe149` all six completed; red_cards had a clean headline, but its summary stated a count
of universes that none of the report's figures gives. A sentence of the form "X of Y universes"
or a share of universes is now kept only when it matches a count or share the report holds
(`acb76dc`). A key error on a column name spelled letter by letter now says so (`7238de8`). At
`068fa85` all six completed again and three defects surfaced. The red_cards baseline was specified
as a Poisson model with `offset=np.log(games)` and its code fitted none, so the headline flip to a
negative binomial with the offset was the offset, not overdispersion; a model whose spec names an
offset or an exposure now fails when the fitted model has none (`908433d`), and replayed on the
red_cards models of the four previous rounds it marks nothing else. In checkout, the filter
options that re-include rows the plan's notes mark as invalid were already kept out of the
headline flip but still counted in the robustness share (40% agreement); they are now excluded
from it too, with a caveat that names each option and its rows (`3ed553a`). The bank summary
listed as accepted an imputation option that had failed its smoke run and never ran; accepted
options that are not in the analysis no longer reach the narrator (`9751a4b`). The hurricanes
summary opened with "0.024 additional expected deaths" for a model of `log1p(alldeaths)`: another
sentence named the log scale, so the check passed. A sentence that carries the original estimate
and speaks of additional or more units with no log scale or percentage is now an error, and the
final summary drops it and states the scale (`9d33e01`); replayed on every summary of the last
five rounds, it marks that sentence and nothing else.


## From `9b95d04` to the final recordings

From `9b95d04` to `6317040` the six recordings were made again in every round, each read universe by
universe, and each defect was fixed with a test and replayed over the earlier rounds before the
next recording. The defects, in the order they surfaced:

- Option code that did not do what its spec said. A default "Keep all sessions" dropped internal
  and short sessions unless a ctx flag was set (checkout, 1 of 22 "keep all" options); a
  "Return the full dataframe unchanged" option excluded internal sessions, and winsorizing options
  also dropped the 82% of bank customers never contacted (5 of 1,679 option codes); an i.i.d.
  baseline fitted HC1 errors; a covariate option said "Set ctx['covariates']" and never wrote it,
  and renamed `get_dummies` columns by position (6 of 1,616 codes); a PCA of nine items z-scored
  each person across the items instead of each item across people (4 of 1,672 codes, the
  marp_religiosity flip depended on it). Each is now a coder or harness check; the replay over
  every recorded option code marks those cases and nothing else.
- Templates that fitted another model than the option named. A model spec that read an outcome an
  earlier step built (`log1p(alldeaths)`) modelled the raw column; a label "with month fixed
  effects" left month out; an adversary option that assigned a covariate the data lacked fitted the
  baseline under its label; an "MM-estimation robust regression" was fitted by OLS (1 of 740 model
  options); a model reported the 97.5% interval as its 95% interval (2 of 740); the negative binomial dispersion was a moment estimate (the hurricanes
  flip was significant only at alpha 0.23; the maximum-likelihood alpha is 1.67, found as the root
  of the profile score). Each now follows the option, or goes to free code.
- Free code on another scale. A marp_norms WLS z-scored the religiosity × norms product after
  multiplying and left the outcome raw under a standardised rule: 0.0747 where the consistent
  estimate is 0.034. The harness now fails a product term that is not the product of its main
  effects' columns, a raw outcome under a standardised rule, and corrects an n that counts the rows
  given instead of the rows fitted; replayed over 181 universes of two rounds, it marks that option
  in its four universes and nothing else.
- Lost options. A model that one-hot encoded and then indexed the data by the dummy names made the
  upstream probe drop both red_cards covariate options with position (three universes left); the
  model is now repaired first, as it is when a formula reads a whole-frame Series while fitting the
  complete cases (a patsy row mismatch that dropped a red_cards option). A covariate option that listed `country_1..23` in ctx and returned
  the data unchanged now fails its own smoke run with the column it should name.
- Reports. "An odds ratio" for a Poisson rate ratio; an absent minimal flip described as "null" or
  "absent"; a count of single-change flips that did not match the garden; universe ids in the
  summary; a covariate option that cut the bank sample from 45,211 to 8,252 rows, now named in a
  caveat (6 bank recordings of 114, all real).
- Labels that named another model. A default called "OLS linear probability model" whose spec
  exponentiated the linear coefficient was fitted as a logit under the OLS label (bank); the
  planner now rejects a linear-probability option under an odds-ratio rule (2 of 126 plans, both
  real). A median quantile regression rebuilt the religiosity score as the item mean, so its "PCA"
  universes repeated the mean ones (1 of 331 model codes overwrite a column an earlier step built).
  A model spec that assigned `y = df['outcome']` from the transform step was fitted on the raw
  deaths, so the log and square-root transforms gave one estimate (14 of 1,315 model options assign
  the outcome that way; all now model the produced column).
- Repairs that answered the wrong failure. Seven marp_norms universes failed when the sandbox
  service let an upload expire, and the runner rewrote six options' code in answer; a repair in
  bank added the missing-value indicators its option's spec forbids, so the option became a no-op.
  A sandbox failure is now retried without touching the code, and a runtime repair is reviewed
  against its spec before it replaces the old code.
- Reports. The original analysis of bank fitted 8,252 of the 45,211 rows that reach its model and
  said nothing (3 of 126 plans now carry a caveat naming the columns whose missing values drop the
  rows); 7 of 51 flip narratives never gave the flipped estimate; a dead model step was described
  as one "the model ignores".

- Checks that rejected sound code. Dummies named after their level (`gender_woman`, `country_France`)
  did not count as built from their covariate, so "Add league and referee country" was dropped
  from red_cards; a Gamma link written `"Log"` was not read as a log link; a covariate option that
  listed `platform_android`, the level `get_dummies(drop_first=True)` drops, failed three repairs
  in a row (4 options in all, both checkout); a model spec that wrote its outcome as
  `converted * 100` to get percentage points lost the checkout default (Borges converts units
  itself). Each now passes with what the code built, and a note says what was substituted.
- Labels that named an interval the run did not compute. statsmodels 0.15 gives Logit, GLM and
  count models the HC0 covariance whatever HC1, HC2 or HC3 is asked (the four standard errors are
  equal); 33 model options in 25 recordings asked for one of them. Reports now say the interval
  is HC0. An option that only divided the result by 100 (same p-value and n; 12 of 10,518 universe
  pairs) is a unit change and treated as a no-op; a quantile regression on an outcome with few
  values gets a caveat; covariates the model put in its design twice are named as a second copy,
  not as dropped covariates (56 traces, all marp_norms).
- Recordings of 5 October (rec33 to rec35, 18 runs). The reviewer was told a covariate option had
  dropped its dummies and failed an option whose code was right (checkout lost "Adjust for platform
  only"); the reviewer now reads the harness note on substituted dummies. A covariate change was
  reported as a re-analysis of the same quantity; it now counts as an estimand change. A cloglog
  link was reported as an odds ratio; links are read from the fitted family, and a complementary
  log-log fit reports a hazard ratio. An option asking for weighted least squares ran unweighted;
  code that drops the weights an option asks for is refused. A Gamma GLM and a probit were
  templated as OLS; families the template does not fit go to free code. A narrator line read
  "verdict:." when no flip existed; that sentence is removed. A transient connection error wrapped
  in another exception ended a bank run; the retry walks the exception's causes. A column the
  template renamed as the second copy of a covariate (`contact_missing_repeat1`) was named in a
  caveat as a dropped covariate; it is now named by the column.
- Recordings of 5 October (rec36 and rec37, 12 runs). The marp_norms headline of rec37 was fitted
  on psychological well-being, not on overall well-being: the default outcome option built a
  column and did not write ctx['outcome'] although its spec said "write to ctx['outcome']", its
  sibling did, and the model fell back to the sibling's outcome. The guard that holds code to the
  ctx keys its spec promises missed the phrase "write to"; it now reads it, and an option must write
  ctx['outcome'] when the other options of its step do. A note that named the z-scored outcome by
  the template's default name, not the outcome read at run time, is what showed it.
  The reviewer called a square-root option unfaithful because the step's shared column was named
  `log_alldeaths_plus1`, quoting a log1p the spec did not contain, and the repair then rewrote
  the code as log1p (two hurricanes options lost). A review that calls an option unfaithful now
  carries a quote, Borges checks that the option's spec contains it, asks once more if it does not,
  and drops the point if the quote still does not match. A quasi-Poisson option fitted
  `scale="X2"` with `cov_type="HC0"`, which statsmodels ignores under a sandwich covariance (the
  interval equalled the Poisson HC0 one to 14 digits); the guard and the model spec now refuse that
  pairing. When every universe with an alternative of one decision failed (bank: the covariate
  option listed missing-value indicators only the default option creates), a caveat now says the
  decision was not tested. `statsmodels.stats.proportion` is allowed in option code (a Wilson
  interval option was lost to the import list twice in 326 recordings).
- A made-up flip (rec38, 2415a4b). The bank run reported CAP THE CALLS reversed to NO CASE FOR A
  CAP under the adversary's "Bayesian logistic regression". After a runtime repair, its code set the
  coefficient to 0 and its variance to 1 whenever the fit was not finite, then returned OR 1.0 with
  an interval [0.5, 2.0] and p 0.5 as a last resort: the flipped universe, OR 1.046 [0.15, 7.8],
  p 0.5165, is exp(N(0, 1)) under seed 42. The same code divided the coefficient by the standard
  deviation of a column it had not standardised and returned the share of draws above 1 as its
  p-value; both reviews passed it. The model guard now refuses fixed numbers (or an identity
  covariance) assigned in a branch that tests isfinite, isnan or isinf, or in an except clause,
  unless the branch raises, and a p-value computed as the mean of a comparison. Over the 389
  distinct model codes recorded, it flags only this option.
- Prefixes read as broken formulas (fin10, 44a43e5). A red_cards repeat failed outright: every
  model option and the re-plan were refused with "unexpected end of formula". The code tested
  term.startswith('C(') to parse the plan's covariates and built "y ~ x + C(g) + " before joining
  them; the guard read both constants as unfinished formulas. Across 25,145 cached LLM replies the
  pattern appears three ways ('C(' 44 times). Accepting any truncated fragment would have reopened
  a deliberate refusal (an unclosed I( call split across constants), so the guard now exempts only
  constants used as startswith/endswith arguments or as the left side of in, and ignores a
  trailing operator; nine of the sixteen refused codes from that run now pass and the other seven
  have real faults.
- An aggregation written for one group (rec40, 95200c8). The checkout recording failed: every
  model option and the re-plan died on "the exposure level 'treatment' is not a value of the
  column 'variant'". The cause was one step earlier: "Group by user_id; compute variant as the
  first variant per user" was coded as if apply() received one user's rows, and returned a single
  row. It passed its smoke run and the model was blamed. The harness now requires a transform or
  feature option that says "group by X", and returns fewer rows than it received, to return one
  row per distinct value of X; a per-group column that keeps every row is untouched. The six
  distinct recorded checkout aggregations pass the new check on the real data.
- A rejected option brought back by a re-plan (rec41, 16f02e7). The red_cards recording reported
  BIAS DETECTED with OR 1.37 on a baseline the judge had rejected. One step's options had all
  failed their smoke runs, the step was re-planned, and the planner proposed the same option the
  judge had refused; the re-plan did not consult the judged ledger. Re-planned options the judge
  already rejected are now dropped (`05d0306`), and red_cards was recorded again at `5070877`.
  None of the other five recordings of that round made a re-plan.
- A fleet seed imported one event at a time (`e295b8f`). Each imported record re-read and
  re-verified the whole identity chain, so a fresh home took seconds per hundred records and the
  runtime queue tests timed out under load. The import now verifies once, chains every event and
  writes once, with the same chain and anchors.
- A headline weighted by its own exposure (the independent refit of the final recordings). The
  bank planner's default model said "weighted logistic regression" without naming a weight; the
  guard that refuses code dropping the weights an option asks for pushed the coder to weight each
  client by `campaign`, the exposure itself, as frequency weights. The recorded headline was OR
  0.9067 [0.9013, 0.9122], p 2.5e-225; unweighted it is 0.8773 [0.8613, 0.8935], p 2.3e-44.
  The verdict holds, the number and its interval did not. The harness now records the weights of
  every statsmodels model and fails the step when the model that reports the estimate weights its
  rows by the exposure column (`80d3ae6`). Of the 10 distinct recorded model codes that weight,
  this is the only one that weights by the exposure; the others use inverse variances or another
  column. bank was recorded again at `6317040`.
- A citation nobody checks (the refit of red_cards). The judge attached a DOI of a
  neuroinflammation paper to the flip's "at least 2 games together" option. Citations are written
  by the planner, adversary or judge and nothing retrieves them; the CLI and the web app now label
  them "cited by the model, not checked" and no longer link them (`43d913c`).
