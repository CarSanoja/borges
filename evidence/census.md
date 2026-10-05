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

The d187b02 batch was stopped after 25 runs because the causes it had found were already fixed;
the next batch ran in full at the fixed commit.

The raw run files of the last two batches are in `evidence/repeats/` (`efe1aa5.tar.gz`,
`cecf187.tar.gz`); `evidence/repeats.md` is generated from the cecf187 batch and
`evidence/adversary-ablation.md` from both.

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
