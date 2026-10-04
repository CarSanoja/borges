from __future__ import annotations

from borges.analysis.coder_checks import option_violations
from borges.analysis.coder_normalise import add_missing_imports, strip_trailing_closer
from borges.analysis.models import AnalysisPlan, Option, Step
from borges.analysis.prompts.coder import build_messages
from borges.analysis.schemas import CoderOutput
from borges.llm.client import LLMClient, Role


async def fresh_recode(
    llm: LLMClient,
    plan: AnalysisPlan,
    step: Step,
    option: Option,
    errors: list[str],
    suffix: str = ":recode",
) -> tuple[str, str | None, str]:
    response = await llm.complete(
        Role.REPAIRER,
        build_messages(plan, step, option, errors[-1] if errors else None, errors),
        key=f"coder:{step.id}.{option.id}{suffix}",
        schema=CoderOutput,
        max_tokens=1500,
    )
    code, _ = strip_trailing_closer(CoderOutput.model_validate(response.parsed).code)
    code, _ = add_missing_imports(code)
    violations = option_violations(code, plan, step, option)
    return code, ("\n".join(violations) if violations else None), response.usage.model
