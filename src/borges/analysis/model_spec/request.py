from __future__ import annotations

from dataclasses import dataclass

from borges.analysis.code_guard_ctx import varying_ctx_keys
from borges.analysis.code_guard_statsmodels import option_intent
from borges.analysis.coder_checks import option_violations
from borges.analysis.model_spec.ctx_covariates import ctx_covariate_names
from borges.analysis.model_spec.derived_exposure import derived_exposure
from borges.analysis.model_spec.prompt import build_spec_messages, correction
from borges.analysis.model_spec.render import render_code
from borges.analysis.model_spec.schema import ModelSpecOutput
from borges.analysis.model_spec.validate import validate_spec
from borges.analysis.model_spec.validate_ctx import ctx_problems
from borges.analysis.model_spec.validate_named_exposure import named_exposure_problems
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


def _problems(plan: AnalysisPlan, step: Step, option: Option, spec: ModelSpecOutput) -> list[str]:
    available = _available_columns(plan, step)
    ctx_names = ctx_covariate_names(plan, step, available) if spec.covariates_from_ctx else []
    found = validate_spec(spec, available, plan.dataset, plan.decision_rule, ctx_names)
    if not spec.supported:
        return found
    varied = "covariates" in varying_ctx_keys(plan, step)
    return [
        *found,
        *ctx_problems(spec, ctx_names, option_intent(option), varied),
        *named_exposure_problems(spec, option.spec, available),
    ]


async def request_template(
    llm: LLMClient,
    plan: AnalysisPlan,
    step: Step,
    option: Option,
    models: list[str] | None = None,
    skipped: list[str] | None = None,
) -> Templated | None:
    pending = sorted(set(varying_ctx_keys(plan, step)) - {"covariates"})
    if pending:
        keys = ", ".join(f"ctx['{k}']" for k in pending)
        _skip(
            skipped, f"the model must read {keys}, chosen by an earlier step, and a template cannot"
        )
        return None
    messages = build_spec_messages(plan, step, option)
    key = f"coder:{step.id}.{option.id}:spec"
    available = _available_columns(plan, step)
    spec = await _ask(llm, messages, key, models, skipped)
    if spec is None:
        return None
    spec = derived_exposure(spec, option.spec, available, plan.dataset)
    problems = _problems(plan, step, option, spec)
    if problems:
        _skip(skipped, "; ".join(problems))
        if not spec.supported:
            return None
        retry = [*messages, *correction(spec, problems)]
        spec = await _ask(llm, retry, f"{key}:retry", models, None)
        if spec is not None:
            spec = derived_exposure(spec, option.spec, available, plan.dataset)
        if spec is None or _problems(plan, step, option, spec):
            return None
        if skipped:
            skipped.pop()
    code = render_code(spec)
    violations = option_violations(code, plan, step, option)
    if violations:
        _skip(skipped, "the rendered code failed the guard: " + "; ".join(violations))
        return None
    return Templated(code, str(spec.family))
