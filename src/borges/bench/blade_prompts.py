from __future__ import annotations

ATTRIBUTION = (
    "Matching prompts adapted from BLADE (Gu et al. 2024, github.com/behavioral-data/BLADE, "
    "blade_bench/eval/llm, Apache-2.0). The variable and model prompts keep BLADE's criteria "
    "and its 5 to 10 similarity scale; the transform prompt is written for this benchmark."
)

SYSTEM = (
    "You are an AI data analysis assistant and an expert in statistical modeling. You compare "
    "two lists of analysis decisions made on the same dataset and report which ones match."
)

CVAR = """Given the research question, the dataset and two lists of conceptual variables, \
carefully match the variables of list A with those of list B. Two variables are similar if \
they would be operationalized in the same way, used in the same way in a statistical model, \
and measure the same concept. Pay attention to the type of variable (IV, DV, control).
Return JSON only, in this format, one entry per matched pair:
{"A1-B2": {"rationale": "<why>", "similarity": <integer 5-10>}}
Scale: 5 somewhat related, 6 moderately related, 7 strongly related but different in details \
that matter, 8 very strongly related and operationalized in a similar way, 9 almost identical, \
10 identical. If nothing matches return {}."""

MODEL = """Given two lists of statistical model specifications written in natural language for \
the same analysis, return ALL pairs that are the same model: the same data would give the same \
results (for example a logistic regression equals a binomial GLM with a logit link, but is not \
a linear regression). Ignore any specific variables or data references.
Return JSON only, in this format:
{"A1-B2": {"rationale": "<why>", "similarity": 10}}
If nothing matches return {}."""

TRANSFORM = """Given two lists of data transformation decisions (filtering rows, deriving or \
recoding variables) made for the same analysis, match the decisions of list A with those of \
list B that do the same thing to the data: the same rows removed, or the same variable \
derived in the same way. Ignore wording and ignore code style.
Return JSON only, in this format:
{"A1-B2": {"rationale": "<why>", "similarity": <integer 5-10>}}
Use 8 or more only when the two decisions would give the same data. If nothing matches return {}."""

INSTRUCTIONS = {"cvar": CVAR, "model": MODEL, "transform": TRANSFORM}


def user_message(kind: str, question: str, schema: str, expert: list[str], agent: list[str]) -> str:
    def block(label: str, items: list[str]) -> str:
        lines = "\n".join(f'  "{i}": {text!r},' for i, text in enumerate(items, 1))
        return f"======List {label}:\n{{\n{lines}\n}}"

    return (
        f"<Instruction>\n{INSTRUCTIONS[kind]}\n</Instruction>\n\n"
        f"Research question: {question}\nDataset schema: {schema}\n\n"
        f"{block('A', expert)}\n{block('B', agent)}\n\nResult:"
    )
