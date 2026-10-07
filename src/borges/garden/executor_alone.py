"""Run one model step straight on the raw data, outside the plan, with the same harness."""

from __future__ import annotations

from borges.analysis import harness
from borges.analysis.model_spec.validate_standardized import reads_standardised
from borges.analysis.models import AnalysisResult, Step
from borges.analysis.row_key import row_key
from borges.garden.executor import GardenExecutor
from borges.garden.executor_errors import SANDBOX_FAILED, failure_detail
from borges.garden.executor_output import read_step_output
from borges.garden.fit_summary import fit_summary


async def run_on_root(
    executor: GardenExecutor, step: Step, fit: dict[str, object] | None = None
) -> tuple[AnalysisResult | None, str | None]:
    """`fit`, when given, receives the rows and design means of the model the step fitted."""
    if executor.root is None:
        raise RuntimeError("GardenExecutor.setup() must be called before run_on_root()")
    option = step.default
    script = harness.render_step(
        step,
        option,
        design_check=executor.design_check,
        full_data_checks=executor.full_data_checks,
        standardised=reads_standardised(executor.plan.decision_rule.metric),
        row_key=row_key(executor.plan.dataset),
    )
    files = {harness.step_filename(step.id, option.id): script.encode()}
    command = harness.step_command(step.id, option.id)
    try:
        run = await executor.backend.run(
            executor.root, command, files=files, timeout_s=executor.step_timeout_s
        )
    except Exception as exc:
        return None, f"{SANDBOX_FAILED}: {exc}"
    if not run.ok:
        return None, failure_detail(run)[0]
    traces, result, problem = read_step_output(
        run.stdout, step.id, option.id, executor.plan.result_scale
    )
    if fit is not None:
        fit.update(fit_summary(traces))
    if problem is not None:
        return None, problem
    if result is None:
        return None, "the implementation produced no result"
    return result, None
