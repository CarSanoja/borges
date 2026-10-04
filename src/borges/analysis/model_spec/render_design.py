from __future__ import annotations

from borges.analysis.model_spec.schema import INTERACTION_COLUMN, ModelSpecOutput


def design_term(spec: ModelSpecOutput) -> str:
    return INTERACTION_COLUMN if spec.moderator is not None else str(spec.exposure)


def _core_columns(spec: ModelSpecOutput) -> list[str]:
    return [c for c in (spec.outcome, spec.exposure, spec.moderator) if c is not None]


def _used_columns(spec: ModelSpecOutput) -> list[str]:
    extras = [c for c in (spec.cluster, spec.offset_log) if c is not None]
    return [*_core_columns(spec), *extras]


def covariate_lines(spec: ModelSpecOutput) -> list[str]:
    core = _core_columns(spec)
    if spec.covariates_from_ctx:
        lines = [
            f"    names = {spec.covariates!r} + [str(c) for c in ctx.get('covariates', [])]",
            f"    names = [c for c in dict.fromkeys(names) if c not in {core!r}]",
        ]
    else:
        names = [c for c in dict.fromkeys(spec.covariates) if c not in core]
        lines = [f"    names = {names!r}"]
    lines.append(f"    used = list(dict.fromkeys({_used_columns(spec)!r} + names))")
    return lines


def frame_lines(spec: ModelSpecOutput) -> list[str]:
    lines = ["    data = df.dropna(subset=used)"]
    if spec.exposure_level is not None:
        lines.append(
            f"    data = data.assign(**{{{spec.exposure!r}: "
            f"(data[{spec.exposure!r}].astype(str) == {spec.exposure_level!r}).astype(float)}})"
        )
    if spec.standardize:
        lines += [
            f"    scaled = {spec.standardize!r}",
            "    data = data.assign(**{c: (data[c].astype(float) - data[c].astype(float).mean())"
            " / (data[c].astype(float).std() or 1.0) for c in scaled})",
        ]
    return lines


ALIAS_TOLERANCE = 1e-7
ALIAS_NOTE = "aliased covariates dropped: "
ALIAS_LINES = [
    "    protected = ['const', *map(str, core.columns)]",
    "    basis = np.zeros((len(exog), 0))",
    "    aliased = []",
    "    for column in list(exog.columns):",
    "        vector = exog[column].to_numpy(dtype=float)",
    "        size = float(np.linalg.norm(vector))",
    "        residual = vector / size if size else vector",
    "        for _ in range(2):",
    "            residual = residual - basis @ (basis.T @ residual)",
    "        size = float(np.linalg.norm(residual))",
    f"        if size >= {ALIAS_TOLERANCE!r}:",
    "            basis = np.column_stack([basis, residual / size])",
    "        elif str(column) not in protected:",
    "            aliased.append(str(column))",
    "    exog = exog.drop(columns=aliased)",
    f"    note = {ALIAS_NOTE!r} + ', '.join(aliased) if aliased else ''",
]


def exog_lines(spec: ModelSpecOutput) -> list[str]:
    if spec.moderator is None:
        core = f"    core = data[[{spec.exposure!r}]].astype(float)"
    else:
        columns = f"[{spec.exposure!r}, {spec.moderator!r}]"
        product = f"data[{spec.exposure!r}].astype(float) * data[{spec.moderator!r}].astype(float)"
        core = f"    core = data[{columns}].astype(float).assign({INTERACTION_COLUMN}={product})"
    return [
        core,
        "    parts = [core]",
        "    numeric = [c for c in names if pd.api.types.is_numeric_dtype(data[c])]",
        "    other = [c for c in names if c not in numeric]",
        "    if numeric:",
        "        parts.append(data[numeric].astype(float))",
        "    if other:",
        "        dummies = pd.get_dummies(data[other].astype(str), drop_first=True, dtype=float)",
        "        parts.append(dummies)",
        "    exog = sm.add_constant(pd.concat(parts, axis=1), has_constant='add')",
        *ALIAS_LINES,
        f"    endog = data[{spec.outcome!r}].astype(float)",
    ]
