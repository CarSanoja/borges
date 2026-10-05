from __future__ import annotations

from collections.abc import Awaitable, Callable

from borges.analysis.coder_checks import option_violations
from borges.analysis.coder_normalise import add_missing_imports, strip_trailing_closer
from borges.analysis.models import AnalysisPlan, Option, Step
from borges.analysis.prompts.coder import build_messages
from borges.analysis.prompts.coder_collision import rewrite_instruction
from borges.analysis.schemas import CoderOutput
from borges.llm.client import LLMClient, Role

CODE_TOKENS = 2500


async def _request(
    llm: LLMClient,
    plan: AnalysisPlan,
    step: Step,
    option: Option,
    messages: list[dict[str, str]],
    key: str,
) -> tuple[str, str | None, str]:
    response = await llm.complete(
        Role.REPAIRER, messages, key=key, schema=CoderOutput, max_tokens=CODE_TOKENS
    )
    code, _ = strip_trailing_closer(CoderOutput.model_validate(response.parsed).code)
    code, _ = add_missing_imports(code)
    violations = option_violations(code, plan, step, option)
    return code, ("\n".join(violations) if violations else None), response.usage.model


async def fresh_recode(
    llm: LLMClient,
    plan: AnalysisPlan,
    step: Step,
    option: Option,
    errors: list[str],
    suffix: str = ":recode",
) -> tuple[str, str | None, str]:
    messages = build_messages(plan, step, option, errors[-1] if errors else None, errors)
    return await _request(llm, plan, step, option, messages, f"coder:{step.id}.{option.id}{suffix}")


def make_rewrite(
    llm: LLMClient, plan: AnalysisPlan
) -> Callable[[Step, Option, Option, str], Awaitable[tuple[str, str | None, str]]]:
    async def rewrite(
        step: Step, option: Option, other: Option, kind: str
    ) -> tuple[str, str | None, str]:
        messages = build_messages(plan, step, option, None)
        note = rewrite_instruction(plan, kind, option, other)
        messages[-1] = {**messages[-1], "content": f"{messages[-1]['content']}\n\n{note}"}
        return await _request(
            llm, plan, step, option, messages, f"coder:{step.id}.{option.id}:{kind}"
        )

    return rewrite
