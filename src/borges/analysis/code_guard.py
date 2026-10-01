from __future__ import annotations

from borges.analysis.models import StepKind

ALLOWED_IMPORTS = frozenset(
    {
        "pandas",
        "numpy",
        "math",
        "scipy",
        "scipy.stats",
        "statsmodels",
        "statsmodels.api",
        "statsmodels.formula.api",
    }
)


def check_code(code: str, kind: StepKind) -> list[str]:
    raise NotImplementedError
