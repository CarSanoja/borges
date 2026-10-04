from __future__ import annotations

import re

from borges.analysis.model_spec.schema import ModelSpecOutput
from borges.analysis.models import AnalysisPlan, Step

ASSIGN = re.compile(r"""ctx\[\s*["']outcome["']\s*\]\s*=\s*([^\n]+)""")
LITERAL = re.compile(r"""^["']([^"']+)["']""")
DEFINITION = "def estimate(df, ctx):"
VARIABLE = "outcome_column"


def ctx_outcome_names(plan: AnalysisPlan, step: Step, available: list[str]) -> list[str] | None:
    """The column names earlier options store in ctx['outcome'], or None if one is not literal."""
    names: list[str] = []
    for earlier in plan.steps:
        if earlier.id == step.id:
            break
        for option in earlier.options:
            text = option.code if option.code is not None else option.spec
            for value in ASSIGN.findall(text):
                literal = LITERAL.match(value.strip())
                if literal is None:
                    return None
                names.append(literal.group(1))
    found = list(dict.fromkeys(names))
    if not found or any(name not in available for name in found):
        return None
    return found


def outcome_instruction(names: list[str]) -> str:
    listed = ", ".join(names)
    return (
        "The outcome is chosen by an earlier step and stored in ctx['outcome'] "
        f"(one of: {listed}). Translate the rest of the option and write outcome as "
        f"'{names[0]}': the rendered code reads ctx['outcome'] when it runs."
    )


def pin_outcome(spec: ModelSpecOutput, names: list[str]) -> ModelSpecOutput:
    if spec.outcome in names:
        return spec
    return spec.model_copy(update={"outcome": names[0]})


def candidate_specs(spec: ModelSpecOutput, names: list[str]) -> list[ModelSpecOutput]:
    return [spec.model_copy(update={"outcome": name}) for name in names]


def read_ctx_outcome(code: str, outcome: str) -> str:
    line = f"    {VARIABLE} = str(ctx.get('outcome', {outcome!r}))"
    body = code.replace(repr(outcome), VARIABLE)
    return body.replace(DEFINITION, f"{DEFINITION}\n{line}", 1)
