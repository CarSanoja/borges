from __future__ import annotations

from borges.analysis.model_spec.schema import ModelSpecOutput
from borges.analysis.models import ColumnProfile, DatasetProfile

TEXT_DTYPES = ("object", "str", "string", "category")


def profile_of(profile: DatasetProfile | None, name: str) -> ColumnProfile | None:
    if profile is None:
        return None
    return next((c for c in profile.columns if c.name == name), None)


def is_text(column: ColumnProfile | None) -> bool:
    return column is not None and column.dtype.startswith(TEXT_DTYPES)


def column_levels(column: ColumnProfile) -> list[str]:
    values = [str(v) for k, v in column.summary.items() if k.startswith("top_")]
    return [v.rsplit(": ", 1)[0] for v in values]


def exposure_problems(spec: ModelSpecOutput, profile: DatasetProfile | None) -> list[str]:
    column = profile_of(profile, spec.exposure) if spec.exposure is not None else None
    if column is None:
        return []
    name, level = spec.exposure, spec.exposure_level
    if not is_text(column):
        if level is not None:
            return [f"exposure '{name}' is numeric, so exposure_level must not be set"]
        if spec.report == "marginal_effect" and column.n_unique > 2:
            return [f"marginal_effect needs a 0/1 exposure; '{name}' has {column.n_unique} values"]
        return []
    if column.n_unique != 2:
        return [f"exposure '{name}' is text with {column.n_unique} levels: only two are allowed"]
    levels = column_levels(column)
    if level is None:
        return [f"exposure '{name}' is text: set exposure_level to the level coded 1 ({levels})"]
    if level not in levels:
        return [f"exposure_level '{level}' is not a level of '{name}' ({levels})"]
    return []
