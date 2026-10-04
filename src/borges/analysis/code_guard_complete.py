"""A model fitted on data with missing values must start from complete cases.

statsmodels raises MissingDataError on a NaN in the outcome or a predictor, so a model option that
never drops incomplete rows fails as soon as an upstream option adds a covariate with a missing
value, and that upstream option is dropped for the model's fault. The formula API drops incomplete
rows itself, so only the array API (sm.OLS, sm.GLM, ...) is checked.
"""

from __future__ import annotations

import ast

from borges.analysis.code_guard_missing import _called, _filters
from borges.analysis.code_guard_statsmodels import MODEL_CLASSES
from borges.analysis.models import DatasetProfile

ARRAY_MODELS = frozenset(name for name in MODEL_CLASSES if name[0].isupper())
MASKS = frozenset({"notna", "notnull", "isna", "isnull"})
MESSAGE = (
    "the data have missing values ({columns}) and this model never drops incomplete rows, so "
    "statsmodels fails as soon as a model column holds one; start with complete cases, "
    "data = df.dropna(subset=[...]) over every column the model uses, and fit on data"
)


def _drops_missing(tree: ast.AST) -> bool:
    if "dropna" in _called(tree) or _filters(tree):
        return True
    for node in ast.walk(tree):
        dropping = (
            isinstance(node, ast.keyword)
            and node.arg == "missing"
            and isinstance(node.value, ast.Constant)
            and node.value.value == "drop"
        )
        masking = (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr in MASKS
        )
        if dropping or masking:
            return True
    return False


def complete_case_violations(code: str, profile: DatasetProfile) -> list[str]:
    missing = [c.name for c in profile.columns if c.n_missing > 0]
    if not missing:
        return []
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return []
    if not _called(tree) & ARRAY_MODELS or _drops_missing(tree):
        return []
    return [MESSAGE.format(columns=", ".join(missing[:5]))]
