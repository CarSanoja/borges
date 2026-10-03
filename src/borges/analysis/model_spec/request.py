from __future__ import annotations

from dataclasses import dataclass

from borges.analysis.code_guard import check_code
from borges.analysis.code_guard_statsmodels import option_intent
from borges.analysis.model_spec.prompt import build_spec_messages
from borges.analysis.model_spec.render import render_code
from borges.analysis.model_spec.schema import ModelSpecOutput
from borges.analysis.model_spec.validate import validate_spec
from borges.analysis.models import AnalysisPlan, Option, Step
from borges.analysis.prompts.coder import _available_columns
from borges.llm.client import LLMClient, LLMError, Role

TEMPLATE_PREFIX = "template: "


@dataclass(frozen=True)
class Templated:
    code: str
    family: str

    @property
    def note(self) -> str:
        return f"{TEMPLATE_PREFIX}{self.family}"


def template_family(note: str | None) -> str | None:
    if note is not None and note.startswith(TEMPLATE_PREFIX):
        return note[len(TEMPLATE_PREFIX) :]
    return None


async def request_template(
    llm: LLMClient,
    plan: AnalysisPlan,
    step: Step,
    option: Option,
    models: list[str] | None = None,
) -> Templated | None:
    try:
        response = await llm.complete(
            Role.CODER,
            build_spec_messages(plan, step, option),
            key=f"coder:{step.id}.{option.id}:spec",
            schema=ModelSpecOutput,
            max_tokens=700,
        )
        spec = ModelSpecOutput.model_validate(response.parsed)
    except (LLMError, ValueError):
        return None
    if models is not None:
        models.append(response.usage.model)
    rule = plan.decision_rule
    if validate_spec(spec, _available_columns(plan, step), plan.dataset, rule):
        return None
    code = render_code(spec)
    if check_code(code, step.kind, option_intent(option)):
        return None
    return Templated(code, str(spec.family))
