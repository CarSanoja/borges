from __future__ import annotations

from dataclasses import dataclass

from borges.analysis.code_guard_ctx import varying_ctx_keys
from borges.analysis.code_guard_statsmodels import option_intent
from borges.analysis.coder_checks import option_violations
from borges.analysis.model_spec.ctx_covariates import ctx_covariate_names
from borges.analysis.model_spec.ctx_outcome import (
    candidate_specs,
    ctx_outcome_names,
    outcome_instruction,
    pin_outcome,
    read_ctx_outcome,
)
from borges.analysis.model_spec.normalise import normalise_spec
from borges.analysis.model_spec.prompt import build_spec_messages, correction
from borges.analysis.model_spec.render import render_code
from borges.analysis.model_spec.schema import ModelSpecOutput
from borges.analysis.model_spec.validate import validate_spec
from borges.analysis.model_spec.validate_ctx import ctx_problems
from borges.analysis.model_spec.validate_marked_exposure import marked_exposure_problems
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


def _problems(
    plan: AnalysisPlan,
    step: Step,
    option: Option,
    spec: ModelSpecOutput,
    outcomes: list[str] | None = None,
) -> list[str]:
    available = _available_columns(plan, step)
    ctx_names = ctx_covariate_names(plan, step, available) if spec.covariates_from_ctx else []
    variants = candidate_specs(spec, outcomes) if outcomes else [spec]
    found = list(
        dict.fromkeys(
            problem
            for variant in variants
            for problem in validate_spec(
                variant, available, plan.dataset, plan.decision_rule, ctx_names
            )
        )
    )
    if not spec.supported:
        return found
    varied = "covariates" in varying_ctx_keys(plan, step)
    return [
        *found,
        *ctx_problems(spec, ctx_names, option_intent(option), varied),
        *named_exposure_problems(spec, option.spec, available),
        *marked_exposure_problems(spec, plan.dataset),
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
    available = _available_columns(plan, step)
    outcomes = ctx_outcome_names(plan, step, available) if pending == ["outcome"] else None
    if pending and outcomes is None:
        keys = ", ".join(f"ctx['{k}']" for k in pending)
        _skip(
            skipped, f"the model must read {keys}, chosen by an earlier step, and a template cannot"
        )
        return None
    messages = build_spec_messages(plan, step, option)
    if outcomes:
        last = messages[-1]
        messages[-1] = {**last, "content": f"{last['content']}\n\n{outcome_instruction(outcomes)}"}
    key = f"coder:{step.id}.{option.id}:spec"

    def tidy(found: ModelSpecOutput) -> ModelSpecOutput:
        found = normalise_spec(found, option.spec, available, plan.dataset)
        return pin_outcome(found, outcomes) if outcomes else found

    spec = await _ask(llm, messages, key, models, skipped)
    if spec is None:
        return None
    spec = tidy(spec)
    problems = _problems(plan, step, option, spec, outcomes)
    if problems:
        _skip(skipped, "; ".join(problems))
        if not spec.supported:
            return None
        retry = [*messages, *correction(spec, problems)]
        spec = await _ask(llm, retry, f"{key}:retry", models, None)
        if spec is not None:
            spec = tidy(spec)
        if spec is None or _problems(plan, step, option, spec, outcomes):
            return None
        if skipped:
            skipped.pop()
    code = render_code(spec)
    if outcomes and spec.outcome is not None:
        code = read_ctx_outcome(code, spec.outcome)
    violations = option_violations(code, plan, step, option)
    if violations:
        _skip(skipped, "the rendered code failed the guard: " + "; ".join(violations))
        return None
    return Templated(code, str(spec.family))
