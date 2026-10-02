from __future__ import annotations

import re

from borges.analysis.models import ColumnProfile, DatasetProfile

FLAG_TOKENS = frozenset(
    {
        "test",
        "tester",
        "internal",
        "staff",
        "employee",
        "bot",
        "crawler",
        "spam",
        "fraud",
        "dup",
        "duplicate",
        "dupe",
        "exclude",
        "excluded",
        "exclusion",
        "outlier",
        "invalid",
        "demo",
        "qa",
    }
)
OUTLIER_SIGMAS = 6.0
MIN_OUTLIER_UNIQUE = 10
FLAG_UNIQUE_MAX = 3


def _tokens(name: str) -> set[str]:
    spaced = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", name)
    return {t for t in re.split(r"[^A-Za-z0-9]+", spaced.lower()) if t}


def _is_flag_name(column: ColumnProfile) -> bool:
    return bool(_tokens(column.name) & FLAG_TOKENS)


def _describe_flag(column: ColumnProfile) -> str:
    detail = ""
    if "share_true" in column.summary:
        detail = f", {column.summary['share_true']:.1%} of rows are true"
    elif column.n_unique <= FLAG_UNIQUE_MAX and column.summary:
        detail = f", values {', '.join(str(v) for v in column.summary.values())}"
    return (
        f"- {column.name} ({column.dtype}, {column.n_unique} distinct values{detail}): "
        "its name suggests it marks test, internal, staff, bot, duplicate or excluded records"
    )


def _outlier_sigmas(column: ColumnProfile) -> float:
    s = column.summary
    if not {"std", "p50", "min", "max"} <= s.keys() or isinstance(s["std"], str):
        return 0.0
    std = float(s["std"])
    if std <= 0:
        return 0.0
    return max(float(s["max"]) - float(s["p50"]), float(s["p50"]) - float(s["min"])) / std


def _describe_outlier(column: ColumnProfile) -> str:
    s = column.summary
    return (
        f"- {column.name}: min {s['min']}, median {s['p50']}, max {s['max']}, "
        f"std {s['std']}; the extremes sit about {_outlier_sigmas(column):.0f} standard "
        "deviations from the median"
    )


def flagged_columns(profile: DatasetProfile) -> tuple[list[ColumnProfile], list[ColumnProfile]]:
    flags = [c for c in profile.columns if _is_flag_name(c)]
    flag_names = {c.name for c in flags}
    outliers = [
        c
        for c in profile.columns
        if c.name not in flag_names
        and c.n_unique >= MIN_OUTLIER_UNIQUE
        and _outlier_sigmas(c) >= OUTLIER_SIGMAS
    ]
    return flags, outliers


def describe_inclusion_candidates(profile: DatasetProfile) -> str:
    flags, outliers = flagged_columns(profile)
    lines: list[str] = []
    if flags:
        lines.append("Columns that look like flags for records that may need excluding:")
        lines.extend(_describe_flag(c) for c in flags)
    if outliers:
        lines.append("Numeric columns with extreme values:")
        lines.extend(_describe_outlier(c) for c in outliers)
    return "\n".join(lines)
