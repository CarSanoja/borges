from __future__ import annotations

from borges.analysis import harness
from borges.analysis.models import AnalysisResult, StepTrace
from borges.analysis.result_scale import convert
from borges.garden.result_interval import interval_error


def read_step_output(
    stdout: str, step_id: str, option_id: str, scale: float
) -> tuple[list[StepTrace], AnalysisResult | None, str | None]:
    where = f"{step_id}/{option_id}"
    try:
        traces, result = harness.parse_output(stdout)
    except Exception as exc:
        return [], None, f"{where}: unparseable output: {exc}"
    if result is not None:
        result, problem = convert(result, scale)
        if problem is None and result is not None:
            problem = interval_error(result)
        if problem is not None:
            return [], None, f"{where}: {problem}"
    mine = [t for t in traces if t.step_id == step_id and t.option_id == option_id]
    return mine, result, None
