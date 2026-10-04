from __future__ import annotations

from borges.analysis.model_spec.schema import RESERVED_COLUMNS, ModelSpecOutput
from borges.analysis.models import ColumnProfile, DatasetProfile, DecisionRule
from borges.analysis.result_scale import detect_scale
from borges.analysis.scale_check import is_ratio_rule

TEXT_DTYPES = ("object", "str", "string", "category")
COUNT_FAMILIES = ("poisson", "negbin")
MAX_FIXED_EFFECT_LEVELS = 50
RATIO_REPORTS = {"logit": "odds_ratio", "poisson": "rate_ratio", "negbin": "rate_ratio"}


def _profile_of(profile: DatasetProfile | None, name: str) -> ColumnProfile | None:
    if profile is None:
        return None
    return next((c for c in profile.columns if c.name == name), None)


def _is_text(column: ColumnProfile | None) -> bool:
    return column is not None and column.dtype.startswith(TEXT_DTYPES)


def _required(spec: ModelSpecOutput) -> list[str]:
    return [
        f"{field} is required when supported is true"
        for field in ("family", "outcome", "exposure")
        if getattr(spec, field) is None
    ]


def _single_columns(spec: ModelSpecOutput) -> list[tuple[str, str]]:
    pairs = [
        ("outcome", spec.outcome),
        ("exposure", spec.exposure),
        ("moderator", spec.moderator),
        ("offset_log", spec.offset_log),
        ("cluster", spec.cluster),
    ]
    return [(label, name) for label, name in pairs if name is not None]


def _column_problems(spec: ModelSpecOutput, available: list[str]) -> list[str]:
    named = [*_single_columns(spec)]
    named += [("covariates", n) for n in spec.covariates]
    named += [("standardize", n) for n in spec.standardize]
    problems = [
        f"{label} column '{name}' is not available when this step runs"
        for label, name in named
        if name not in available
    ]
    problems += [
        f"column '{name}' is a reserved name of the template"
        for _, name in named
        if name in RESERVED_COLUMNS
    ]
    return problems


def _role_problems(spec: ModelSpecOutput) -> list[str]:
    problems = []
    if spec.exposure is not None and spec.exposure == spec.outcome:
        problems.append("exposure and outcome must be different columns")
    if spec.moderator is not None and spec.moderator in (spec.exposure, spec.outcome):
        problems.append("moderator must differ from exposure and outcome")
    literal = {spec.outcome, spec.exposure, spec.moderator, *spec.covariates}
    problems += [
        f"standardize column '{name}' is not the outcome, exposure, moderator or a covariate"
        for name in spec.standardize
        if name not in literal
    ]
    if spec.family in RATIO_REPORTS and spec.outcome in spec.standardize:
        problems.append(f"the {spec.family} outcome cannot be standardized")
    return problems


def _consistency_problems(spec: ModelSpecOutput) -> list[str]:
    problems = []
    if spec.report != "coefficient" and RATIO_REPORTS.get(spec.family or "") != spec.report:
        problems.append(f"report {spec.report} is not available for family {spec.family}")
    if spec.cov_type == "cluster" and spec.cluster is None:
        problems.append("cov_type cluster needs a cluster column")
    if spec.cov_type != "cluster" and spec.cluster is not None:
        problems.append("cluster is set but cov_type is not cluster")
    if spec.offset_log is not None and spec.family not in COUNT_FAMILIES:
        problems.append("offset_log is only available for poisson and negbin")
    return problems


def _outcome_problems(spec: ModelSpecOutput, profile: DatasetProfile | None) -> list[str]:
    if spec.outcome is None:
        return []
    column = _profile_of(profile, spec.outcome)
    if column is None:
        return []
    problems = []
    if spec.family in RATIO_REPORTS and _is_text(column):
        problems.append(f"outcome '{spec.outcome}' is not numeric")
    if spec.family == "logit" and not _is_text(column):
        low, high = column.summary.get("min"), column.summary.get("max")
        binary = column.n_unique <= 2
        if (
            not binary
            or (isinstance(low, float) and low < 0)
            or (isinstance(high, float) and high > 1)
        ):
            problems.append(f"logit outcome '{spec.outcome}' must be binary 0/1")
    if spec.family in COUNT_FAMILIES and column.summary.get("min", 0.0) < 0:
        problems.append(f"count outcome '{spec.outcome}' has negative values")
    return problems


def _numeric_problems(spec: ModelSpecOutput, profile: DatasetProfile | None) -> list[str]:
    numeric = [spec.exposure, spec.moderator, spec.offset_log, *spec.standardize]
    return [
        f"column '{name}' is not numeric"
        for name in numeric
        if name is not None and _is_text(_profile_of(profile, name))
    ]


def _level_problems(
    spec: ModelSpecOutput, profile: DatasetProfile | None, ctx_covariates: list[str]
) -> list[str]:
    names = list(spec.covariates)
    if spec.covariates_from_ctx:
        names += ctx_covariates
    problems = []
    for name in dict.fromkeys(names):
        column = _profile_of(profile, name)
        if _is_text(column) and column is not None and column.n_unique > MAX_FIXED_EFFECT_LEVELS:
            problems.append(
                f"{name} has {column.n_unique} levels: use it as the cluster column, "
                "not as dummy fixed effects"
            )
    return problems


def _scale_problems(spec: ModelSpecOutput, rule: DecisionRule | None) -> list[str]:
    if rule is None:
        return []
    if detect_scale(rule.metric) != 1.0 and spec.family != "ols":
        return [
            "the decision rule is a difference in proportions, which this family does not "
            "report as a coefficient"
        ]
    if is_ratio_rule(rule) and (spec.family == "ols" or spec.report == "coefficient"):
        return ["the decision rule compares a ratio with 1.0, so report a ratio"]
    return []


def validate_spec(
    spec: ModelSpecOutput,
    available: list[str],
    profile: DatasetProfile | None = None,
    rule: DecisionRule | None = None,
    ctx_covariates: list[str] | None = None,
) -> list[str]:
    if not spec.supported:
        return [f"the spec is marked unsupported: {spec.reason}"]
    missing = _required(spec)
    if missing:
        return missing
    return [
        *_column_problems(spec, available),
        *_role_problems(spec),
        *_consistency_problems(spec),
        *_outcome_problems(spec, profile),
        *_numeric_problems(spec, profile),
        *_level_problems(spec, profile, ctx_covariates or []),
        *_scale_problems(spec, rule),
    ]
