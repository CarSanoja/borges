from __future__ import annotations

from dataclasses import dataclass

from borges.analysis.code_guard import check_code
from borges.analysis.code_guard_statsmodels import option_intent
from borges.analysis.model_spec.ctx_covariates import ctx_covariate_names
from borges.analysis.model_spec.prompt import build_spec_messages, correction
from borges.analysis.model_spec.render import render_code
from borges.analysis.model_spec.schema import ModelSpecOutput
from borges.analysis.model_spec.validate import validate_spec
from borges.analysis.models import AnalysisPlan, Option, Step
from borges.analysis.prompts.coder import _available_columns
from borges.llm.client import LLMClient, LLMError, Role

TEMPLATE_PREFIX = "template: "
SKIP_PREFIX = "template skipped: "
SKIP_LIMIT = 240


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


def join_notes(skips: list[str], notes: list[str]) -> str | None:
    return "; ".join([*skips, *notes[:1]]) or None


def _skip(skipped: list[str] | None, reason: str) -> None:
    if skipped is not None:
        skipped.append(f"{SKIP_PREFIX}{reason}"[:SKIP_LIMIT])


async def _ask(
    llm: LLMClient,
    messages: list[dict[str, str]],
    key: str,
    models: list[str] | None,
    skipped: list[str] | None,
) -> ModelSpecOutput | None:
    try:
        response = await llm.complete(
            Role.CODER, messages, key=key, schema=ModelSpecOutput, max_tokens=700
        )
        spec = ModelSpecOutput.model_validate(response.parsed)
    except LLMError:
        return None
    except ValueError as exc:
        _skip(skipped, f"the spec did not parse: {exc}")
        return None
    if models is not None:
        models.append(response.usage.model)
    return spec


def _problems(plan: AnalysisPlan, step: Step, spec: ModelSpecOutput) -> list[str]:
    available = _available_columns(plan, step)
    ctx_names = ctx_covariate_names(plan, step, available) if spec.covariates_from_ctx else []
    return validate_spec(spec, available, plan.dataset, plan.decision_rule, ctx_names)


async def request_template(
    llm: LLMClient,
    plan: AnalysisPlan,
    step: Step,
    option: Option,
    models: list[str] | None = None,
    skipped: list[str] | None = None,
) -> Templated | None:
    messages = build_spec_messages(plan, step, option)
    key = f"coder:{step.id}.{option.id}:spec"
    spec = await _ask(llm, messages, key, models, skipped)
    if spec is None:
        return None
    problems = _problems(plan, step, spec)
    if problems:
        _skip(skipped, "; ".join(problems))
        if not spec.supported:
            return None
        retry = [*messages, *correction(spec, problems)]
        spec = await _ask(llm, retry, f"{key}:retry", models, None)
        if spec is None or _problems(plan, step, spec):
            return None
        if skipped:
            skipped.pop()
    code = render_code(spec)
    violations = check_code(code, step.kind, option_intent(option))
    if violations:
        _skip(skipped, "the rendered code failed the guard: " + "; ".join(violations))
        return None
    return Templated(code, str(spec.family))
