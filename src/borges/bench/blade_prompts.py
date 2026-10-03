from __future__ import annotations

import json

from borges.bench import blade_examples as ex

ATTRIBUTION = (
    "Matching prompts adapted from BLADE (Gu et al. 2024, github.com/behavioral-data/BLADE, "
    "blade_bench/eval/llm, Apache-2.0). The variable and model prompts keep BLADE's criteria, "
    "its worked example, its numbered-JSON lists and its 5 to 10 similarity scale; BLADE matches "
    "transforms by data values instead, so the transform prompt is written for this benchmark in "
    "the same shape."
)

SYSTEM = (
    "You are an AI data analysis assistant and an expert in statistical modeling. You compare "
    "two lists of analysis decisions made on the same dataset and report which ones match."
)

CVAR = """Given the research question, the dataset and two lists of conceptual variables, \
carefully match the variables of list A with those of list B, ensuring a strong correspondence \
between the matched points. Two variables are similar if they would be operationalized in the \
same way, used in the same way in a statistical model, and measure the same concept. Pay \
attention to the type of variable (IV, DV, control) and how it fits the research question. \
Refrain from matching points with only superficial similarities.
Return JSON only, one entry per matched pair (A is the first list, B the second):
{"A1-B2": {"rationale": "<why A1 and B2 are nearly identical>", "similarity": <integer 5-10>}}
Scale: 5 somewhat related (same concept, different angle), 6 moderately related, 7 strongly \
related but different in details that matter, 8 very strongly related and operationalized in a \
similar way, 9 almost identical, 10 identical. Compare every item of A with every item of B \
before answering. If no match is found, output an empty JSON object."""

MODEL = """Given two lists of statistical model specifications written in natural language for \
the same analysis, return ALL COMBINATIONS of matching pairs between list A and list B. Match \
only models that are the same for conducting the analysis: given the same data, the \
specification would lead to the same results. For example "logistic regression" is equivalent \
to a "binomial GLM with a logit link function", and OLS is a linear regression, but a logistic \
regression is not a linear regression. Standard-error options (robust, clustered) do not change \
the model family. If the specification references specific data or variables, IGNORE them.
Return JSON only, one entry per matched pair (A is the first list, B the second):
{"A1-B2": {"rationale": "<why A1 and B2 are the same model>", "similarity": 10}}
Compare every item of A with every item of B before answering. If no model matches, output an \
empty JSON object."""

TRANSFORM = """Given two lists of data transformation decisions (filtering rows, deriving or \
recoding variables, aggregating) made for the same analysis, return ALL pairs where a decision \
of list A and a decision of list B do the same thing to the data: the same rows removed, or the \
same variable derived in the same way. Ignore wording, column names and code style. Decisions \
that only choose covariates or keep every row do not transform data and match nothing but \
another decision that does the same.
Return JSON only, one entry per matched pair (A is the first list, B the second):
{"A1-B2": {"rationale": "<why A1 and B2 do the same>", "similarity": <integer 5-10>}}
Use 8 or more only when both decisions would give the same data. Compare every item of A with \
every item of B before answering. If nothing matches, output an empty JSON object."""

INSTRUCTIONS = {"cvar": CVAR, "model": MODEL, "transform": TRANSFORM}
CVAR_HEAD = (ex.CVAR_QUESTION, ex.CVAR_SCHEMA)
EXAMPLES = {
    "cvar": (*CVAR_HEAD, ex.CVAR_A, ex.CVAR_B, ex.CVAR_RESULT),
    "model": (*CVAR_HEAD, ex.MODEL_A, ex.MODEL_B, ex.MODEL_RESULT),
    "transform": (
        ex.TRANSFORM_QUESTION,
        ex.TRANSFORM_SCHEMA,
        ex.TRANSFORM_A,
        ex.TRANSFORM_B,
        ex.TRANSFORM_RESULT,
    ),
}


def numbered(items: list[str]) -> str:
    return json.dumps({str(i): text for i, text in enumerate(items, 1)}, indent=2)


def lists(a: str, b: str) -> str:
    return f"======List A:\n```\n{a}\n```\n======List B:\n```\n{b}\n```"


def user_message(kind: str, question: str, schema: str, expert: list[str], agent: list[str]) -> str:
    ex_question, ex_schema, a, b, result = EXAMPLES[kind]
    example = lists(json.dumps(a, indent=2), json.dumps(b, indent=2))
    head = f"Research question: {ex_question}\nDataset schema: {ex_schema}\n"
    return (
        f"<Instruction>\n{INSTRUCTIONS[kind]}\n</Instruction>\n\n"
        f"<Example>\n{head}{example}\nResult:\n```json\n{json.dumps(result, indent=2)}\n```\n"
        "</Example>\n\n"
        f"Research question: {question}\nDataset schema: {schema}\n"
        f"{lists(numbered(expert), numbered(agent))}\nResult:\n"
    )
