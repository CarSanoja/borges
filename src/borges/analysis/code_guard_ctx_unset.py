"""A ctx key the code reads that no step before it ever sets.

fertility_vote on 7 October, run 22: the next-onset step's code branched on
ctx.get('next_onset_option') == 'next_onset_add', a key no step sets, so the formula of its spec
sat in a dead branch, the onset became the start of the last period, every cycle day was clipped
to 28, the window filter kept no woman and the run failed. A run starts from an empty ctx, so a
key that no earlier step mentions, and that the code does not write itself, is never there. A
read with an empty collection as its default, ctx.get('covariates', []), is left alone: the code
already does what it should when the key is absent.
"""

from __future__ import annotations

import ast
import re

from borges.analysis.code_guard_ctx import COLUMN_KEYS, _ctx_access
from borges.analysis.code_guard_ctx_spec import _written_keys
from borges.analysis.models import AnalysisPlan, Step

MESSAGE = (
    "this code reads ctx['{key}'], which no earlier step sets (a run starts from an empty ctx), "
    "so whatever depends on it always takes the same path; do what the spec says without it"
)


def _mentioned(key: str, texts: list[str]) -> bool:
    quoted = re.compile(rf"""["']{re.escape(key)}["']""")
    return any(quoted.search(text) for text in texts)


COLLECTIONS = (ast.List, ast.Dict, ast.Tuple, ast.Set)


def _relied_on(tree: ast.AST) -> set[str]:
    """Keys read without an empty-collection default, whose absence changes what the code does."""
    keys: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Subscript) and isinstance(node.ctx, ast.Store):
            continue
        key = _ctx_access(node)
        if not (isinstance(key, ast.Constant) and isinstance(key.value, str)):
            continue
        defensive = (
            isinstance(node, ast.Call)
            and len(node.args) == 2
            and isinstance(node.args[1], COLLECTIONS)
        )
        if not defensive:
            keys.add(key.value)
    return keys


def unset_ctx_violations(code: str, plan: AnalysisPlan, step: Step) -> list[str]:
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return []
    read = _relied_on(tree)
    if not read:
        return []
    index = next((i for i, s in enumerate(plan.steps) if s.id == step.id), None)
    if index is None:
        return []
    earlier = [t for s in plan.steps[:index] for o in s.options for t in (o.spec, o.code or "")]
    written = _written_keys(tree)
    return [
        MESSAGE.format(key=key)
        for key in sorted(read - written - COLUMN_KEYS)
        if not _mentioned(key, earlier)
    ]
