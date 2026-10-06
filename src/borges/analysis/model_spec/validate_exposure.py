from __future__ import annotations

from borges.analysis.model_spec.schema import ModelSpecOutput
from borges.analysis.models import ColumnProfile, DatasetProfile

TEXT_DTYPES = ("object", "str", "string", "category")
MAX_LISTED_LEVELS = 12


def profile_of(profile: DatasetProfile | None, name: str) -> ColumnProfile | None:
    if profile is None:
        return None
    return next((c for c in profile.columns if c.name == name), None)


def is_text(column: ColumnProfile | None) -> bool:
    return column is not None and column.dtype.startswith(TEXT_DTYPES)


def column_levels(column: ColumnProfile) -> list[str]:
    values = [str(v) for k, v in column.summary.items() if k.startswith("top_")]
    return [v.rsplit(": ", 1)[0] for v in values]


def _binary_problems(name: str | None, column: ColumnProfile) -> list[str]:
    low, high = column.summary.get("min"), column.summary.get("max")
    if column.n_unique > 2 or (low is not None and high is not None and (low, high) != (0, 1)):
        return [f"marginal_effect needs a 0/1 exposure; '{name}' has {column.n_unique} values"]
    return []


def _threshold_problems(spec: ModelSpecOutput, profile: DatasetProfile | None) -> list[str]:
    if spec.exposure_level is not None:
        return ["set exposure_level for a text exposure or exposure_threshold for a cut, not both"]
    if is_text(profile_of(profile, str(spec.exposure))):
        return [f"exposure '{spec.exposure}' is text: a cut needs a numeric column"]
    return []


def exposure_problems(spec: ModelSpecOutput, profile: DatasetProfile | None) -> list[str]:
    if spec.exposure_threshold is not None:
        return _threshold_problems(spec, profile)
    name, level = spec.exposure, spec.exposure_level
    if spec.report == "marginal_effect" and name in spec.standardize:
        return [f"marginal_effect needs the exposure '{name}' unscaled: remove it from standardize"]
    column = profile_of(profile, name) if name is not None else None
    if column is None:
        return []
    if not is_text(column):
        if level is not None:
            return [f"exposure '{name}' is numeric, so exposure_level must not be set"]
        if spec.report == "marginal_effect" and spec.family == "logit":
            return _binary_problems(name, column)
        return []
    if column.n_unique > MAX_LISTED_LEVELS:
        return [
            f"exposure '{name}' is text with {column.n_unique} levels: too many for one indicator"
        ]
    levels = column_levels(column)
    if level is None:
        return [f"exposure '{name}' is text: set exposure_level to the level coded 1 ({levels})"]
    if level not in levels:
        return [f"exposure_level '{level}' is not a listed level of '{name}' ({levels})"]
    return []


def moderator_problems(spec: ModelSpecOutput, profile: DatasetProfile | None) -> list[str]:
    name, level = spec.moderator, spec.moderator_level
    if name is None:
        return ["moderator_level is set but there is no moderator"] if level is not None else []
    column = profile_of(profile, name)
    if column is None:
        return []
    if not is_text(column):
        return (
            [f"moderator '{name}' is numeric, so moderator_level must not be set"] if level else []
        )
    levels = column_levels(column)
    if level is None:
        return [f"moderator '{name}' is text: set moderator_level to the level coded 1 ({levels})"]
    if level not in levels:
        return [f"moderator_level '{level}' is not a listed level of '{name}' ({levels})"]
    return []
