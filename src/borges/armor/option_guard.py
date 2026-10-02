from __future__ import annotations

from borges.analysis.models import AnalysisPlan, Option, Step
from borges.armor.findings import Finding
from borges.armor.injection import MODEL_OUTPUT, screen_text
from borges.armor.report import Action, ArmorDecision, ArmorReport
from borges.armor.text_guard import summarise


class ToolPoisoningError(RuntimeError):
    """A model output that steers later agents sits somewhere the plan cannot drop."""


def option_findings(option: Option) -> list[Finding]:
    parts = (option.label, option.rationale, option.spec, option.source or "")
    return screen_text("\n".join(parts), MODEL_OUTPUT)


def step_findings(step: Step) -> list[Finding]:
    return screen_text("\n".join((step.title, step.description, *step.produces)), MODEL_OUTPUT)


def poison_decision(field: str, action: Action, findings: list[Finding]) -> ArmorDecision:
    detail, quote = summarise(findings)
    return ArmorDecision(action, "tool_poisoning", field, detail, len(findings), quote)


def poison_reason(findings: list[Finding]) -> str:
    detail, _ = summarise(findings)
    return f"armor: the option text tries to steer the analysis or code ({detail})"


def screen_plan(plan: AnalysisPlan) -> tuple[dict[tuple[str, str], list[Finding]], ArmorReport]:
    """Planner output goes to the coder: flag steering options; fail when it is in a fixed place."""
    report = ArmorReport()
    flagged: dict[tuple[str, str], list[Finding]] = {}
    fixed = screen_text(plan.estimand, MODEL_OUTPUT)
    if fixed:
        report.add(poison_decision("planner:estimand", "block", fixed))
        raise ToolPoisoningError(
            f"the planner estimand carries steering text: {poison_reason(fixed)}"
        )
    for step in plan.steps:
        text = step_findings(step)
        if text:
            report.add(poison_decision(f"planner:step:{step.id}", "block", text))
            raise ToolPoisoningError(f"planner step {step.id} carries steering text")
        for option in step.options:
            findings = option_findings(option)
            if not findings:
                continue
            if option.is_default:
                report.add(poison_decision(f"planner:{step.id}.{option.id}", "block", findings))
                raise ToolPoisoningError(
                    f"the default option {step.id}.{option.id} carries steering text"
                )
            flagged[(step.id, option.id)] = findings
            report.add(poison_decision(f"planner:{step.id}.{option.id}", "drop", findings))
    return flagged, report
