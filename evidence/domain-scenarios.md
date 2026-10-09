# Domain scenarios: eight analyses a user would bring, with a planted answer

On 9 October 2026 Borges was run live (Nemotron on Nebius Token Factory, ConTree sandboxes) on
eight synthetic datasets from four domains: an audit firm's internal reviews, a hospital
department, a K-12 district and a retail bank. The audit firm, *Northbridge Assurance LLP*, is
fictional, and so are every name, e-mail address (on `.example`) and account number in the data.

Each dataset hides a known answer and a trap a real analyst meets. The answer was computed with
statsmodels before any run (`evidence/domains/truth.json`). Each request (`*.request.json`) is
what a user would type: a question, a decision rule, column notes and, in two cases, the memo of
an earlier analysis. Two cases ask in Spanish.

The first four target confounding: the answer changes once the right covariates are in the model.
The second four target the design: nested units, a question about how likely something is asked
of a count, an exposure given to whole schools, and a Spanish CSV with a rare outcome.

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

A rerun of the clinic case after the template fix still gave the old answer
(r_20261009T070254_637cec): memory reused the model code that the previous coder version had
written for the same option. A memory now counts only when the latest approved version of its
agent wrote it, and the next rerun dropped 22 stale entries.

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

## Reproduce

```bash
uv run python evidence/domains/confounding_cases.py
uv run python evidence/domains/design_cases.py
```

Each writes its CSVs next to the script and updates `truth.json`. Upload a CSV and post its
request to `/api/runs` with `"llm": "nebius"`.
