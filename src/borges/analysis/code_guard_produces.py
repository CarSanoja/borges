from __future__ import annotations

import re

from borges.analysis.code_guard_ctx import COLUMN_KEYS, CTX_WRITE, ctx_read_pattern
from borges.analysis.code_guard_overwrite import overwritten
from borges.analysis.models import AnalysisPlan, Step

PRODUCING = frozenset({"transform", "feature"})
GLOB = re.compile(r"[*?\[]")
STAR = re.compile(r"(\w+?)_?\*")
Products = dict[str, tuple[list[str], set[str], set[str]]]
COUNT_OR_BINARY_FIT = re.compile(
    r"\b(?:Poisson|NegativeBinomial\w*|GeneralizedPoisson|ZeroInflated\w*|Logit|Probit|Binomial)\b",
    re.IGNORECASE,
)
OUTCOME_READ = re.compile(r"""\b(?:endog|y)\s*=\s*\w+\[\s*["'](\w+)["']\s*\]""")
FIT_OUTCOME = re.compile(
    r"\b(?:GLM|Poisson|NegativeBinomial\w*|GeneralizedPoisson|ZeroInflated\w*|Logit|Probit)"
    r"""\(\s*\w+\[\s*["'](\w+)["']\s*\]"""
)
FORMULA_OUTCOME = re.compile(r"""["']\s*(\w+)\s*~""")
DENOMINATOR = re.compile(r"\b(?:offset|exposure)\s*=\s*([^\n]*)")
COLUMN_READ = re.compile(r"""\w+\[\s*["'](\w+)["']\s*\]""")
LEADING_NAME = re.compile(r"^\s*([A-Za-z_]\w*)")


def _mention(name: str) -> re.Pattern[str]:
    return re.compile(rf"(?<![\w.]){re.escape(name)}(?!\w)")


def _quoted(name: str) -> re.Pattern[str]:
    return re.compile(rf"""["']{re.escape(name)}["']""")


def _texts(step: Step) -> list[str]:
    return [option.code or option.spec for option in step.options]


def _carriers(writer: Step, names: list[str]) -> set[str]:
    keys: set[str] = set()
    for text in _texts(writer):
        for key, value in CTX_WRITE.findall(text):
            if any(_mention(name).search(value) for name in names):
                keys.add(key)
    return keys


def _family(column: str, columns: list[str]) -> set[str]:
    stem = re.sub(r"\d+$", "", column)
    if stem == column:
        return {column}
    return {c for c in columns if re.fullmatch(re.escape(stem) + r"\d+", c)}


def _sources(writer: Step, names: list[str], columns: list[str]) -> set[str]:
    """The dataset columns the writer's options name, from which a model would rebuild it."""
    texts = _texts(writer)
    raw = [c for c in columns if c not in names]
    found: set[str] = set()
    for column in raw:
        if any(_mention(column).search(text) for text in texts):
            found |= _family(column, raw)
    stems = {stem for text in texts for stem in STAR.findall(text)}
    return found | {c for c in raw if any(c.startswith(stem) for stem in stems)}


def unused_products(plan: AnalysisPlan, step: Step) -> Products:
    index = next(i for i, s in enumerate(plan.steps) if s.id == step.id)
    earlier = plan.steps[:index]
    columns = [c.name for c in plan.dataset.columns]
    found: Products = {}
    for position, writer in enumerate(earlier):
        names = [n for n in writer.produces if n not in COLUMN_KEYS and not GLOB.search(n)]
        if writer.kind not in PRODUCING or len(writer.options) < 2 or not names:
            continue
        if not all(any(_mention(n).search(t) for n in names) for t in _texts(writer)):
            continue
        between = [t for s in earlier[position + 1 :] for t in _texts(s)]
        if any(_mention(name).search(text) for name in names for text in between):
            continue
        found[writer.title] = (names, _carriers(writer, names), _sources(writer, names, columns))
    return found


def _denominators(code: str) -> set[str]:
    """Columns read as an offset or exposure, directly or through a variable assigned from them."""
    found: set[str] = set()
    for argument in DENOMINATOR.findall(code):
        found |= set(COLUMN_READ.findall(argument))
        for name in LEADING_NAME.findall(argument):
            assigned = re.findall(rf"^\s*{re.escape(name)}\s*=\s*(.*)$", code, re.MULTILINE)
            found |= {c for value in assigned for c in COLUMN_READ.findall(value)}
    return found


def _raw_outcome(code: str, sources: set[str]) -> bool:
    """A count or binary model needs the raw count or 0/1 column as its outcome, and a rate model
    the raw denominator as its offset, so reading the columns an earlier step turned into a rate is
    not rebuilding the transform. An audit run (r_20261009T104019_338034) built exceptions per item
    tested in one step and fitted a Poisson model of the exceptions with log(items) as its offset;
    the outcome sat in a formula and the denominator in offset=, so the default model was refused
    on every attempt and the run failed."""
    if not COUNT_OR_BINARY_FIT.search(code):
        return False
    read = {source for source in sources if _mention(source).search(code)}
    outcome = {
        *OUTCOME_READ.findall(code),
        *FIT_OUTCOME.findall(code),
        *FORMULA_OUTCOME.findall(code),
    }
    return bool(read) and read <= outcome | _denominators(code)


def products_read_violations(code: str, products: Products) -> list[str]:
    """A model that rebuilds an earlier product from its raw columns is refused; a model that
    touches neither the product nor the columns it is built from simply does not use it."""
    problems = []
    for title, (names, carriers, sources) in sorted(products.items()):
        rebuilt = overwritten(code, names)
        if rebuilt:
            listed = ", ".join(f"'{name}'" for name in rebuilt)
            problems.append(
                f"the earlier step '{title}' builds {listed} in different ways, but this code "
                f"assigns {listed} itself, so it replaces what that step built and the choice has "
                "no effect in this option; read the column as the earlier step left it"
            )
            continue
        if any(_quoted(name).search(code) for name in names):
            continue
        if any(ctx_read_pattern(key).search(code) for key in carriers):
            continue
        if sources and not any(_mention(source).search(code) for source in sources):
            continue
        if _raw_outcome(code, sources):
            continue
        listed = ", ".join(f"'{name}'" for name in names)
        problems.append(
            f"the earlier step '{title}' offers different ways to build {listed}, but this code "
            "reads none of them, so that choice would have no effect in this option; use the "
            f"column the earlier step created ({listed}) instead of rebuilding it from raw columns"
        )
    return problems
