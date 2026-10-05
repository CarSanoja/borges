from __future__ import annotations

from borges.analysis.model_spec.schema import INTERACTION_COLUMN, ModelSpecOutput

INPUT_FAULT = "the earlier step that builds it"
CONSTANT_EXPOSURE = (
    " has the same value in every row, so it is collinear with the intercept and its effect "
    f"cannot be estimated: {INPUT_FAULT} produced a constant. A threshold taken from a numpy "
    "median, percentile or quantile is NaN when the column has missing values, and no row then "
    "passes it. The pandas median and quantile methods skip missing values"
)


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


FRACTIONAL_LEVEL = (
    "the exposure is coded 1 only where {column} equals {level} exactly, but {column} is a "
    "numeric column with fractional values, so one value is not a group; to cut it, code 1 for "
    "values at or above the cut after dropping the rows where {column} is missing"
)


def _indicator_lines(column: str, level: str) -> list[str]:
    return [
        f"    hit = data[{column!r}].astype(str) == {level!r}",
        f"    numeric = pd.api.types.is_numeric_dtype(data[{column!r}])",
        f"    binary = numeric and set(pd.unique(data[{column!r}])) <= {{0, 1}}",
        f"    if numeric and not binary and not (data[{column!r}] % 1 == 0).all():",
        f"        raise ValueError({FRACTIONAL_LEVEL.format(level=level, column=column)!r})",
        "    if not hit.any() and not binary:",
        "        raise ValueError(",
        f"            'the exposure level ' + {level!r} + ' is not a value of the column ' + "
        f"{column!r}",
        "        )",
        "    if hit.any():",
        f"        data = data.assign(**{{{column!r}: hit.astype(float)}})",
    ]


def _varies_lines(column: str) -> list[str]:
    return [
        f"    if len(data) and data[{column!r}].nunique() < 2:",
        f"        raise ValueError('the exposure ' + {column!r} + {CONSTANT_EXPOSURE!r})",
    ]


def frame_lines(spec: ModelSpecOutput) -> list[str]:
    lines = [
        "    data = df.dropna(subset=used)",
        "    finite = [c for c in used if pd.api.types.is_numeric_dtype(data[c])]",
        "    data = data[np.isfinite(data[finite].astype(float)).all(axis=1)]",
    ]
    if spec.exposure_level is not None:
        lines += _indicator_lines(str(spec.exposure), spec.exposure_level)
    if spec.exposure_threshold is not None:
        column, cut = str(spec.exposure), float(spec.exposure_threshold)
        lines.append(
            f"    data = data.assign(**{{{column!r}: "
            f"(data[{column!r}].astype(float) >= {cut!r}).astype(float)}})"
        )
    lines += _varies_lines(str(spec.exposure))
    if spec.standardize:
        lines += [
            f"    scaled = {spec.standardize!r}",
            "    data = data.assign(**{c: (data[c].astype(float) - data[c].astype(float).mean())"
            " / (data[c].astype(float).std() or 1.0) for c in scaled})",
        ]
    return lines


ALIAS_TOLERANCE = 1e-7
ALIAS_NOTE = "aliased covariates dropped: "
TANGLED_NOTE = "; covariates that rebuild the exposure with them dropped: "
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
    "    kept = [c for c in exog.columns if c not in aliased]",
    "    tangled = []",
    "    for column in aliased:",
    "        target = exog[column].to_numpy(dtype=float)",
    "        weights = np.linalg.lstsq(exog[kept].to_numpy(dtype=float), target, rcond=None)[0]",
    "        sizes = np.abs(weights) * exog[kept].abs().max().to_numpy(dtype=float)",
    f"        floor = {ALIAS_TOLERANCE!r} * (float(np.abs(target).max()) or 1.0)",
    "        involved = [c for c, size in zip(kept, sizes) if size > floor]",
    "        if any(c in core.columns for c in involved):",
    "            tangled += [c for c in involved if c not in protected]",
    "    tangled = list(dict.fromkeys(tangled))",
    "    exog = exog.drop(columns=aliased + tangled)",
    f"    note = {ALIAS_NOTE!r} + ', '.join(aliased) if aliased else ''",
    f"    note += {TANGLED_NOTE!r} + ', '.join(tangled) if tangled else ''",
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
        "    labels = pd.Series(exog.columns.map(str))",
        "    repeats = labels.groupby(labels).cumcount()",
        "    exog.columns = [f'{c}_repeat{n}' if n else c for c, n in zip(labels, repeats)]",
        *ALIAS_LINES,
        f"    endog = data[{spec.outcome!r}].astype(float)",
    ]
