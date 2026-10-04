from __future__ import annotations

import re

from borges.analysis.code_guard_ctx import COLUMN_KEYS, CTX_WRITE, ctx_read_pattern
from borges.analysis.models import AnalysisPlan, Step

PRODUCING = frozenset({"transform", "feature"})
GLOB = re.compile(r"[*?\[]")
Products = dict[str, tuple[list[str], set[str]]]


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


def unused_products(plan: AnalysisPlan, step: Step) -> Products:
    index = next(i for i, s in enumerate(plan.steps) if s.id == step.id)
    earlier = plan.steps[:index]
    found: Products = {}
    for position, writer in enumerate(earlier):
        names = [n for n in writer.produces if n not in COLUMN_KEYS and not GLOB.search(n)]
        if writer.kind not in PRODUCING or len(writer.options) < 2 or not names:
            continue
        between = [t for s in earlier[position + 1 :] for t in _texts(s)]
        if any(_mention(name).search(text) for name in names for text in between):
            continue
        found[writer.title] = (names, _carriers(writer, names))
    return found


def products_read_violations(
    code: str, products: dict[str, tuple[list[str], set[str]]]
) -> list[str]:
    problems = []
    for title, (names, carriers) in sorted(products.items()):
        if any(_quoted(name).search(code) for name in names):
            continue
        if any(ctx_read_pattern(key).search(code) for key in carriers):
            continue
        listed = ", ".join(f"'{name}'" for name in names)
        problems.append(
            f"the earlier step '{title}' offers different ways to build {listed}, but this code "
            "reads none of them, so that choice would have no effect in this option; use the "
            f"column the earlier step created ({listed}) instead of rebuilding it from raw columns"
        )
    return problems
