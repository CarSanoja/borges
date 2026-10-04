from __future__ import annotations

import ast

NAN_SAFE = {"median": "nanmedian", "percentile": "nanpercentile", "quantile": "nanquantile"}
NUMPY_NAMES = frozenset({"np", "numpy"})


def nan_threshold_violations(tree: ast.AST) -> list[str]:
    """A data step that takes a threshold from np.median, np.percentile or np.quantile gets NaN
    when the column has a missing value, and every comparison with NaN is False."""
    violations = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
            continue
        owner = node.func.value
        if not isinstance(owner, ast.Name) or owner.id not in NUMPY_NAMES:
            continue
        safe = NAN_SAFE.get(node.func.attr)
        if safe is None:
            continue
        violations.append(
            f"line {node.lineno}: np.{node.func.attr}(...) returns NaN when the column has a "
            "missing value, and every comparison with NaN is False, so a threshold built from it "
            "marks no row; use the pandas method, which skips missing values "
            f"(df[col].median(), df[col].quantile(q)), or np.{safe}"
        )
    return violations


DECOMPOSITIONS = frozenset(
    {"PCA", "TruncatedSVD", "FactorAnalysis", "svd", "svds", "eig", "eigh", "eigs"}
)
ORIENTING = frozenset({"corrcoef", "corr", "corrwith", "sign", "copysign"})


def _called(tree: ast.AST) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            names.add(func.attr if isinstance(func, ast.Attribute) else getattr(func, "id", ""))
    return names


def component_sign_violations(tree: ast.AST) -> list[str]:
    """The sign of a principal component or factor is arbitrary: it can differ between a sample
    and the full data, so a data step that builds one must orient it by the data."""
    called = _called(tree)
    if not called & DECOMPOSITIONS or called & ORIENTING:
        return []
    return [
        "the sign of a principal component or factor score is arbitrary and can differ between a "
        "sample and the full data: orient it by the data, so that higher scores mean higher item "
        "values, for example `if np.corrcoef(score, items.mean(axis=1))[0, 1] < 0: score = "
        "-score`"
    ]
