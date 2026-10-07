from __future__ import annotations

from dataclasses import dataclass, field

from borges.analysis.models import AnalysisPlan, AnalysisResult
from borges.garden.executor import GardenExecutor
from borges.garden.models import Universe
from borges.garden.verify import TOLERANCE
from borges.runs.models import RunSnapshot
from borges.sandbox.backend import BranchBackend


@dataclass
class Reproduction:
    universe_id: str
    recorded: Universe
    rerun: Universe
    baseline_recorded: Universe | None
    baseline_rerun: Universe | None
    mismatches: list[str] = field(default_factory=list)

    @property
    def matches(self) -> bool:
        return not self.mismatches


def _differences(label: str, rerun: Universe, recorded: Universe) -> list[str]:
    if rerun.result is None or recorded.result is None:
        return [f"{label}: no result ({rerun.error or 'recorded universe has none'})"]
    return _result_differences(label, rerun.result, recorded.result) + _verdict(
        label, rerun, recorded
    )


def _verdict(label: str, rerun: Universe, recorded: Universe) -> list[str]:
    if rerun.verdict == recorded.verdict:
        return []
    return [f"{label}: verdict {rerun.verdict} != recorded {recorded.verdict}"]


def _result_differences(label: str, rerun: AnalysisResult, recorded: AnalysisResult) -> list[str]:
    fields = ("estimate", "ci_low", "ci_high", "p_value")
    out = [
        f"{label}: {name} {getattr(rerun, name):.10g} != recorded {getattr(recorded, name):.10g}"
        for name in fields
        if abs(getattr(rerun, name) - getattr(recorded, name)) > TOLERANCE
    ]
    if rerun.n != recorded.n:
        out.append(f"{label}: n {rerun.n} != recorded {recorded.n}")
    return out


async def reproduce_universe(
    backend: BranchBackend,
    plan: AnalysisPlan,
    data: bytes,
    snapshot: RunSnapshot,
    universe_id: str,
    step_timeout_s: float,
) -> Reproduction:
    recorded = snapshot.garden.universes[universe_id]
    baseline_recorded = snapshot.garden.baseline
    executor = GardenExecutor(
        backend,
        plan,
        data,
        emit=None,
        reuse_prefixes=False,
        step_timeout_s=step_timeout_s,
        design_check=any(t.design for t in recorded.traces),
        full_data_checks=False,
    )
    await executor.setup()
    is_baseline = baseline_recorded is None or baseline_recorded.id == universe_id
    baseline_rerun = (
        None if is_baseline else await executor.run_universe(plan.default_choices(), "baseline")
    )
    rerun = await executor.run_universe(recorded.choices, recorded.kind)
    mismatches = _differences("universe", rerun, recorded)
    if baseline_rerun is not None and baseline_recorded is not None:
        mismatches += _differences("baseline", baseline_rerun, baseline_recorded)
    return Reproduction(
        universe_id,
        recorded,
        rerun,
        None if is_baseline else baseline_recorded,
        baseline_rerun,
        mismatches,
    )


def _result_line(universe: Universe) -> str:
    result = universe.result
    if result is None:
        return f"no result ({universe.error})"
    return (
        f"estimate {result.estimate:.4f} CI [{result.ci_low:.4f}, {result.ci_high:.4f}] "
        f"p={result.p_value:.4g} n={result.n} -> {universe.verdict}"
    )


def _design_warning(universe: Universe) -> str | None:
    for trace in universe.traces:
        design = trace.design
        if design and design.get("deficient"):
            return (
                f"WARNING: the model's design matrix is rank-deficient (rank {design.get('rank')} "
                f"of {design.get('columns')} columns); the recording predates the design check "
                "and its confidence interval is not trustworthy"
            )
    return None


def reproduction_lines(case_id: str, plan: AnalysisPlan, rep: Reproduction) -> list[str]:
    changed = ", ".join(f"{s}={rep.recorded.choices[s]}" for s in rep.recorded.changed)
    lines = [
        f"case {case_id}, universe {rep.universe_id} ({changed or 'baseline choices'})",
        f"re-executed {len(plan.steps)} steps on the case dataset with the local backend",
        f"rerun:    {_result_line(rep.rerun)}",
        f"recorded: {_result_line(rep.recorded)}",
    ]
    if rep.baseline_rerun is not None and rep.baseline_recorded is not None:
        lines.append(f"baseline rerun:    {_result_line(rep.baseline_rerun)}")
        lines.append(f"baseline recorded: {_result_line(rep.baseline_recorded)}")
    if rep.matches:
        flip = ""
        if rep.baseline_rerun is not None and rep.baseline_rerun.verdict != rep.rerun.verdict:
            flip = f"; flip {rep.baseline_rerun.verdict} -> {rep.rerun.verdict} reproduced"
        lines.append(f"MATCH: estimate, CI, p-value, n and verdict equal the recording{flip}")
        warning = _design_warning(rep.rerun)
        if warning:
            lines.append(warning)
    else:
        lines.append("MISMATCH with the recording:")
        lines.extend(f"  {item}" for item in rep.mismatches)
    return lines
