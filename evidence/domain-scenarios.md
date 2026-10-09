# Domain scenarios: nineteen analyses a user would bring, with a planted answer

On 9 October 2026 Borges was run live (Nemotron on Nebius Token Factory, ConTree sandboxes) on
nineteen synthetic datasets from four domains: an audit firm's internal reviews, a hospital
department, a K-12 district and a retail bank. The audit firm, *Northbridge Assurance LLP*, is
fictional, and so are every name, e-mail address (on `.example`) and account number in the data.

Each dataset hides a known answer and a trap a real analyst meets. The answer was computed with
statsmodels before any run (`evidence/domains/truth.json`). Each request (`*.request.json`) is
what a user would type: a question, a decision rule, column notes and, in two cases, the memo of
an earlier analysis. Six cases ask in Spanish.

The first four target confounding: the answer changes once the right covariates are in the model.
The second four target the design: nested units, a question about how likely something is asked
of a count, an exposure given to whole schools, and a Spanish CSV with a rare outcome. The last
four are edge cases: a numeric exposure with values missing for the riskiest rows, a 2 % outcome
with a site that never used the treatment, 24 students measured twice in long format, and a
rollout staggered across branches over a trend. The last four test inputs: yes/no flags typed by
hand, a time to readmission censored at 90 days, an outcome already in percent under a rule in
percentage points, and a European CSV with thousands dots and decimal commas. The last three
test the rule and the headers: Spanish headers with accents and symbols and notes written against
them, a rule on "at least half a point per hour", and a rate ratio that must fall below 0.8.

## Results

"First run" is the run that found the gap; "after" is the run after the fix, at the commit named.

| Scenario | Planted answer and trap | First run | Gap found | After the fix |
|---|---|---|---|---|
| Audit: did the analytics tool cut budget overruns? | No effect (0); the tool went to larger clients, who overrun less | Wrong: TOOL CUTS OVERRUNS, 100 % robust (r_20261009T023828_e093b0) | The judge scored adjusting for confounders as "changes the estimand" | Flip found: adjusting for client size gives −0.003, NO CLEAR EFFECT; robustness 88 % (r_20261009T025032_460e5d) |
| Bank: are women approved less at the same risk profile? (Spanish) | No conditional gap; the raw gap comes from income | Flip found but called "another question" (r_20261009T023829_b0bc39) | Same: confounding read as an estimand change | Flip reported as adjusting for the risk profile (r_20261009T025033_b95eb2) |
| K-12: does tutoring work? (Spanish) | +3.0 points | Correct: 2.85 (r_20261009T023829_64b3d7) | Summary in English | Summary in Spanish (see the fraud case) |
| Clinic: did the triage protocol speed diagnosis? | −0.10 log minutes with a staffing trend; −0.13 adjusted for the trend | Right direction, about twice too large: −0.215 (r_20261009T023829_01a30c) | Month dummies rebuild a protocol that starts at a date; the run failed until they were named | Open: the planner does not build a numeric time trend, so the trend is not separated |
| Audit: did quality reviews cut audit adjustments? Asked as "confirm ...; the partners expect yes" | −0.147 log rate (−0.57 adjustments per engagement); reviews went to riskier clients; 40 partners | Correct: REVIEWS CUT ADJUSTMENTS, −0.595 (r_20261009T065046_56b2c6) | The judge rejected partner-clustered errors, "not 30 partners" (there are 40): it could not see the data | The judge sees the distinct values of each column an option names |
| Clinic: are patients on the new discharge protocol less likely to be readmitted? | −0.32 log odds, p 0.02 adjusted; the protocol runs on two of four wards | Wrong: NO CLEAR EFFECT, −0.042, p 0.051 (r_20261009T065046_4433e5) | Adjusting for ward, which defines the protocol: the template kept one ward dummy and compared ward A with C and D | Correct: PROTOCOL CUTS READMISSIONS, −0.041, p 0.017, ward left out with the reason (r_20261009T070801_6239a1) |
| K-12: did a curriculum adopted by 5 of 10 schools raise scores? | +2.0, not detectable with 10 schools: p 0.20 clustered, 0.004 if the schools are ignored | Run failed (r_20261009T065046_af1a24) | The few-clusters check told the repair to use robust errors, the wrong answer here | Correct: NO CLEAR EFFECT, p 0.2298, the exact t(9) reference; the judge rejects errors that ignore the schools (r_20261009T070255_7d0a7c) |
| Bank: did the new alert model cut fraud? (Spanish `;` CSV, decimal commas, BOM; 1.3 % fraud) | −0.81 log odds, about −1.1 points | Correct: −1.09 points (r_20261009T065047_3f2868); CSV read with the right types | Summary in English; the judge rejected client-clustered errors, "not 30 clients" (there are 3,000) | Summary in Spanish, numbers checked against the English (r_20261009T070802_2fc5a8) |
| Audit: do more manager review hours lower the chance of a restatement? | −0.0047 per hour on the probability (−0.069 log odds); complex clients get more hours, and hours are missing mostly for them | Right sign, wrong scale: the logit coefficient −0.068 and a probit alternative −0.035, which the summary read as the effect "roughly halving" (r_20261009T083215_3c1abc) | The marginal-effect template refused a numeric exposure, and free code reported raw coefficients under a rule on a probability | Correct: −0.00471 per hour, probit −0.00477, "a spread of about 0.00006" (r_20261009T084632_39cf88) |
| Clinic: does a new anticoagulant raise major bleeds? 2 % bleed; the rural site never stocks it and has no bleeds | +2.4 points without the rural site (+1.33 log odds) | Run failed (r_20261009T083216_35c688) | The 200-row smoke sample held no bleed, so every model of the outcome failed | Correct: MORE BLEEDS, +2.4 points [1.3, 3.5] (r_20261009T083806_4e3faa) |
| K-12: did a summer reading program raise scores? (Spanish; 24 students before and after, long format) | +4.375 paired, p 8.7e-7; p 0.20 if the pairs are ignored | Refused at upload: 48 rows, "needs at least 50" | The floor's reason, that fewer rows "cannot be told apart from noise", is false for a paired design | Correct: +4.375, p 8.7e-7, n 24, summary in Spanish (r_20261009T083806_696661) |
| Bank: did a new call-centre script cut complaints? (Spanish; staggered across 30 branches, rising trend) | −3.0; −0.41, p 0.26 if months are pooled | Correct: −3.049 with branch and month fixed effects (r_20261009T083216_fcaffe) | None | — |
| Audit: do controls walkthroughs cut material findings? Flags typed as Yes, yes, YES , Y, No, N | −0.080 on the probability; riskier engagements get more walkthroughs | Correct: −0.082 (r_20261009T085133_89649e) | None | — |
| Clinic: does a discharge protocol delay readmission? Time censored at 90 days, 66 % never readmitted | log hazard ratio −0.545 (Cox); +7.0 days if the censoring is ignored | Run failed (r_20261009T085134_fe4c15); two more attempts failed as each gap below was fixed | A Cox option ran as an OLS of the days; the planner wrote R's Surv() and a statsmodels API that does not exist; the harness refused PHReg for having no intercept; the coefficient guard refused positions found by name; "exposure=new_protocol" read as an offset | Correct: PROTOCOL DELAYS READMISSION, −0.5449, p 4e-6, equal to the Cox fit (r_20261009T093901_079f20) |
| K-12: did tutoring raise the percent of proficient students? Outcome 0-100, rule in percentage points | +6.27 points adjusted | Correct: +6.2702 (r_20261009T085134_43c1c4) | None | — |
| Bank: does a fee waiver raise the average balance? (Spanish; `;` CSV with 1.234,56 and dd/mm/yyyy dates) | +404 euros adjusted for income, randomised waiver | Correct: +404.107 (r_20261009T085134_401637), but the check added this morning for a moved origin refused a days-since-sign-up covariate counted from another date | The moved-origin check applied to every column, not only to columns the plan cuts | Correct, the covariate kept and reported as a no-op (r_20261009T092811_a0e3b8) |
| Bank: do clients with an assigned advisor take more products? (Spanish; headers "Antigüedad (años)", "¿Asesor asignado?" with Sí/No; notes keyed by those headers) | rate ratio 1.153 adjusted for tenure; 1.44 raw | Right answer, 1.150 (r_20261009T104019_378c8a), but the columns were stored as antig_edad_a_os_ and _asesor_asignado_ and all three notes were dropped without a word | Accented letters became underscores, and notes matched only the stored names | Columns antiguedad_anios, asesor_asignado; the three notes reach the agents; 1.1528 (r_20261009T110345_7b552c) |
| K-12: does each weekly hour of tutoring add at least half a point? Rule: > 0.5 | 0.678 per hour, interval [0.46, 0.90]; one-sided p 0.053 against 0.5 | AT LEAST HALF A POINT PER HOUR with no caveat (r_20261009T104019_6d1535) | The p-value tests no effect, not 0.5, and the report did not say the interval reaches 0.5 | Same verdict, with a caveat: the interval includes 0.5, so the data show an effect but not that it is past 0.5 (r_20261009T110345_bf6487) |
| Audit: did a new sampling method cut exceptions per item tested by at least 20 %? Rule: rate ratio < 0.8 | 0.694, interval [0.656, 0.734] | Run failed (r_20261009T104019_338034) | The planner built a rate column, and the check that a model reads an earlier step's product refused a Poisson model of the raw count with log(items) as its offset on every attempt | Correct: 0.6936 [0.655, 0.734], the rate step reported as having no effect (r_20261009T110346_6e9334) |

A rerun of the clinic case after the template fix still gave the old answer
(r_20261009T070254_637cec): memory reused the model code that the previous coder version had
written for the same option. A memory now counts only when the latest approved version of its
agent wrote it, and the next rerun dropped 22 stale entries.

The review-hours case was rerun three more times after the fixes, because a correct answer once
is not a correct product:

- r_20261009T101518_df1978: the planner's default filled missing review hours with 0 (−0.00085,
  biased toward zero, with "blank when not logged" in the column notes), and an adversary option,
  "manager fixed effects via demeaning", put the hours minus each manager's mean beside the hours
  themselves. With both in the model the reported coefficient is the effect of the managers'
  means, the comparison the option meant to remove, and it came out as the minimal flip.
- r_20261009T102422_ac9695, after the fixes below: the judge rejected filling with 0 (0.2) and
  the original analysis dropped those rows (−0.00471, correct), and the report named the 195
  engagements left out. The flip was now "no covariates", accepted at 0.6 although the judge's own
  reason said it "leaves confounding in the estimate".
- r_20261009T102930_e204b8, after the confounder rule: −0.00471, robustness 1.0, no flip. The
  same "no covariates" option, judged again on that plan, scores 0.3; the adjusted ones keep 0.9
  and 0.8. The randomised fee-waiver case, rerun as a control (r_20261009T102930_f3f450), still
  accepts the unadjusted comparison at 0.9 "because the exposure was assigned at random".

## What changed

Each gap was fixed at its root, with a unit test and, where it applies, an end-to-end harness test:

- **Confounders are not a change of question.** For a question about what an exposure does, or a
  comparison at equal profiles, adjusting for a pre-exposure confounder estimates the same effect
  (judge prompt and `garden/effect_question.py`).
- **The judge sees the data it reasons about.** It gets the number of distinct values of every
  column an option names (`analysis/prompts/notes.py`).
- **Few clusters, exposure assigned to whole clusters.** The clustering stays, with t critical
  values on clusters minus one degrees of freedom below 30 clusters, and the repair is no longer
  told to drop it (`analysis/harness_cluster_count.py`).
- **A categorical covariate that defines the exposure is dropped whole** and reported as left out
  (`analysis/model_spec/render_alias.py`).
- **Memories from a superseded agent version are ignored** (`memory/approvals.py`).
- **A question that asks for a conclusion is opened**, and the report says so
  (`armor/loaded_question.py`).
- **A question about how likely something is, answered on a count**, gets a caveat naming the
  outcome the analysis used (`garden/likelihood_question.py`).
- **The summary is written in the question's language** when every number and verdict label of
  the checked English summary survives the translation (`analysis/narrative_language.py`).
- **Person names in role columns and medical record numbers are redacted** before any model sees
  them (`armor/pii_names.py`, `armor/pii_patterns.py`).
- **A rare outcome reaches the smoke sample.** The rarer value of every two-valued column gets 20
  rows of the sample when the data has them (`analysis/smoke_sample.py`).
- **A rule on a probability gets a probability.** The template reports the average slope for a
  numeric exposure, and a Logit, Probit or binomial GLM coefficient fails the step under such a
  rule with the code for the marginal effect (`analysis/model_spec/validate_exposure.py`,
  `analysis/harness_result_checks.py`).
- **A table needs 20 rows, not 50** (`api/uploads.py`).
- **Cox models run with statsmodels' PHReg.** The planner and the coder are told how it is called,
  a Cox option no longer falls to the OLS template, the harness does not ask a Cox model for an
  intercept, a failed PHReg call gets a repair hint (`analysis/harness_phreg.py`), and a position
  found from the term's name passes the coefficient guard.
- **A moved origin is refused only for a column some option cuts** (`analysis/smoke_origin.py`).
- **The rows the original analysis leaves out are named.** When its data steps keep less than
  95 % of the uploaded rows, a caveat names each step and how many rows it drops
  (`garden/filtered_rows.py`).
- **The exposure beside its own demeaned copy fails the step** (`analysis/harness_within_copy.py`):
  two regressors whose difference is constant within groups, one of them centred in each group.
- **A missing exposure or outcome is dropped, not filled with a constant**, unless the notes say a
  blank stands for that value; the judge scores such a fill below 0.3.
- **Dropping a named confounder is below acceptance in a causal question** on observational data
  (score under 0.6); with a randomised exposure the unadjusted comparison stays.
- **Uploaded headers keep their letters** ("Antigüedad (años)" is antiguedad_anios), notes written
  against the original headers reach their columns, and a note that names no column is reported
  (`analysis/column_names.py`).
- **Spanish rules are read on their scale**: "puntos porcentuales", "probabilidad", "proporción",
  "riesgo relativo" and "razón de tasas", and English "relative risk"; a ratio rule is checked for
  a ratio at any positive threshold, not only 1.
- **A rate model may read the raw count and its offset** instead of an earlier rate column
  (`analysis/code_guard_produces.py`).
- **A positive verdict whose interval reaches a threshold other than no effect gets a caveat**
  (`garden/threshold_interval.py`).

## Still open

- The clinic trend: Nemotron Super adds the arrival month as a categorical covariate instead of a
  numeric trend, so a before/after design with a pre-existing trend overstates the effect.
- The bank's default covariate set holds the debt ratio but not income; the flip to the right
  answer is found, and the default is not yet the full risk profile.
- Captions, caveats and labels stay in English when the question is in another language; only
  the summary is translated.
- A planner alternative can contradict its own rationale (fertility_social, "committed = 1 if
  Relationship == 1" for "single is answer 1 only"); the orientation check refuses it, so the
  result is not wrong, but the alternative is lost.
- The planner still proposes filling a missing exposure with 0 as its default at times; the judge
  rejects it and the original analysis falls back to the best accepted option.
- A percent outcome (0 to 100) under a rule in percentage points lost a WLS alternative to the unit
  check; the check now tells the code to divide by 100, tested but not yet seen in a live run.
- Restoring the registry seed and publishing again reuses version numbers; a server that had
  imported the first seed keeps the old definition under that number and refuses live runs as
  "unpublished" until the change is approved in its own registry.

## Reproduce

```bash
uv run python evidence/domains/confounding_cases.py
uv run python evidence/domains/design_cases.py
uv run python evidence/domains/edge_cases.py
uv run python evidence/domains/input_cases.py
uv run python evidence/domains/rule_cases.py
```

Each writes its CSVs next to the script and updates `truth.json`. Upload a CSV and post its
request to `/api/runs` with `"llm": "nebius"`.
