from __future__ import annotations

from typing import Any

from borges.analysis.models import AnalysisPlan, AnalysisResult, Option, StepTrace
from borges.analysis.prompts import compact_json, messages

WRITE_SYSTEM = """You write one Python function that carries out a statistical analysis exactly \
as the user describes it, from the raw data to the estimate. Signature: def estimate(df, ctx), \
where df is the raw data as profiled and ctx is a dict you may ignore. Return a dict with the \
keys estimate, ci_low, ci_high, p_value and n: the coefficient or difference the decision rule's \
metric names, its 95% confidence interval and p-value, and the number of rows the model used. \
Do every step the analysis says, in the way it says, and nothing it does not say: no other \
exclusion, imputation, covariate, recoding or transformation. Keep every row the analysis keeps: \
drop a row only where the analysis drops it or where the model cannot use a missing value, and \
when the analysis gives a value by hand for some rows (for rows whose inputs are missing, say), \
set that value after computing the others and keep those rows. Code 0/1 indicators as 0 and 1. \
If the fit fails, raise a ValueError; never return fixed numbers in its place. Import only \
pandas, numpy, statsmodels and scipy: no other module, not even datetime or math (use pandas for \
dates, e.g. pd.to_timedelta and .dt.days, and numpy for arithmetic). No file, network or system \
access, no print. Return only the code."""

FIX_SYSTEM = """An analysis was split into steps, each coded separately; run in order, the \
default option of every step should carry out the user's analysis. It does not: the step-by-step \
code gives a different result from two independent implementations of the same analysis, each \
written as one script, which agree with each other. Find the steps whose code departs from the \
user's analysis: a filter that keeps other rows, an exclusion or imputation the analysis does not \
make, a different coding of a variable, a different model or standard error. Use the row counts \
on the full data and the reference script to locate it. For each such step, return the corrected \
code of its default option: the same function name and signature, reading the columns the earlier \
steps pass on and producing the columns the later steps read, doing what the user's analysis \
says. When another option of the same step has the same defect, return its corrected code too, \
keeping what that option decides. If a default spec itself contradicts the analysis, return the \
corrected spec as well. A step whose own option of the user's analysis could not run shows it \
under analysis_option_that_could_not_run, with its last error, while another option stands in as \
default; when the gap comes from that step, return code for that option, under its option_id, \
doing what its spec says: it becomes the step's default again. fit_difference, when present, \
names by their row key the raw rows the reference fits and the step-by-step code does not (and \
the reverse), with their raw values, and gives the mean of every design column in both fits: \
use it to find the step that drops or keeps those rows, or builds a column with another coding. \
Its where_the_step_by_step_code_loses_them reads the step-by-step code's own data after each \
step: the step after which those rows are gone, and the values earlier steps built for them just \
before it. A built value that is missing or differs from what its step's spec gives for those \
rows points at the step that built it, not at the step that then dropped them. \
Change nothing else."""


REBUILD_SYSTEM = """An analysis was split into steps, each coded separately; run in order, the \
default option of every step should carry out the user's analysis. It does not: two independent \
implementations of the analysis, each written as one script, agree with each other and differ from \
the step-by-step result, and targeted repairs of single steps did not close the gap. Rewrite the \
code of the default option of EVERY step so that running them in order computes exactly what the \
reference script computes. Take each step's part of the computation from the reference script: \
the rows it keeps, the values it sets by hand, how each indicator is coded (which group is 1), the \
model, its terms and its standard errors. Keep each step's role (a filter keeps rows, a transform \
or feature step writes its columns, the model step returns the result), its function name and \
signature, the exact names the step must produce, and every column and ctx key later steps read. \
Return one fix per step, under the default's option_id, with the corrected spec when the default \
spec departs from the analysis. fit_difference, when present, says which rows and codings differ."""


def _result(result: AnalysisResult) -> dict[str, Any]:
    return result.model_dump(include={"estimate", "ci_low", "ci_high", "p_value", "n"})


def build_write_messages(
    plan: AnalysisPlan, attempt: int, feedback: str | None = None
) -> list[dict[str, str]]:
    payload: dict[str, Any] = {
        "question": plan.question,
        "decision_rule": plan.decision_rule,
        "analysis": plan.analysis,
        "dataset": plan.dataset,
        "attempt": attempt,
    }
    if feedback:
        payload["previous_code_failed"] = feedback
    return messages(WRITE_SYSTEM, compact_json(payload))


def build_fix_messages(
    plan: AnalysisPlan,
    traces: list[StepTrace],
    ours: AnalysisResult,
    theirs: AnalysisResult,
    reference_code: str,
    dropped: dict[str, tuple[Option, str | None]] | None = None,
    evidence: dict[str, object] | None = None,
    rebuild: bool = False,
) -> list[dict[str, str]]:
    rows = {t.step_id: [t.rows_before, t.rows_after] for t in traces}
    dropped = dropped or {}
    steps = [
        {
            "step_id": step.id,
            "title": step.title,
            "kind": step.kind,
            "rows_before_after_on_full_data": rows.get(step.id),
            "options": [
                {
                    "option_id": option.id,
                    "default": option.id == step.default.id,
                    "spec": option.spec,
                    "code": option.code,
                }
                for option in step.options
            ],
            **(
                {
                    "analysis_option_that_could_not_run": {
                        "option_id": dropped[step.id][0].id,
                        "spec": dropped[step.id][0].spec,
                        "last_error": dropped[step.id][1],
                    }
                }
                if step.id in dropped
                else {}
            ),
        }
        for step in plan.steps
    ]
    payload = {
        "analysis": plan.analysis,
        "decision_rule": plan.decision_rule,
        "steps": steps,
        "step_by_step_result": _result(ours),
        "reference_result": _result(theirs),
        "reference_code": reference_code,
        **({"fit_difference": evidence} if evidence else {}),
    }
    return messages(REBUILD_SYSTEM if rebuild else FIX_SYSTEM, compact_json(payload))
