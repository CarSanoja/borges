"""How the template drops covariates the exposure's estimate cannot be separated from.

A covariate that is an exact linear combination of earlier columns is dropped, as R's lm does,
and so are the covariates that rebuild the exposure with it. A categorical covariate that
rebuilds the exposure by itself is dropped whole first: a clinic run (r_20261009T065046_4433e5)
adjusted a protocol that wards A and B adopted for ward, the rank check dropped ward_D and ward_C,
and the ward_B kept made the exposure's coefficient a contrast of ward A with wards C and D
(-0.042, p = 0.051, where the effect adjusted for the patients' risk was significant). The
harness then reports the whole covariate as left out because it rebuilds the exposure.
"""

from __future__ import annotations

ALIAS_TOLERANCE = 1e-7
ALIAS_NOTE = "aliased covariates dropped: "
TANGLED_NOTE = "; covariates that rebuild the exposure with them dropped: "
REBUILT_NOTE = "covariates that rebuild the exposure by themselves left out: "
WHOLE_LINES = [
    "    sources = {f'{c}_{v}': c for c in other for v in data[c].astype(str).unique()}",
    "    target = core.iloc[:, 0].to_numpy(dtype=float)",
    f"    floor = {ALIAS_TOLERANCE!r} * (float(np.abs(target).max()) or 1.0)",
    "    members = {}",
    "    for name in exog.columns:",
    "        members.setdefault(sources.get(str(name)), []).append(name)",
    "    for column in other:",
    "        own = members.get(column, [])",
    "        if not own:",
    "            continue",
    "        span = exog[['const', *own]].to_numpy(dtype=float)",
    "        fitted = span @ np.linalg.lstsq(span, target, rcond=None)[0]",
    "        if float(np.abs(target - fitted).max()) <= floor:",
    "            exog = exog.drop(columns=own)",
]
ALIAS_LINES = [
    *WHOLE_LINES,
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
