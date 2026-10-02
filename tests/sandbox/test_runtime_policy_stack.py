from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from borges.analysis import harness
from borges.sandbox.local_backend import LocalBackend
from tests.sandbox.policy_support import run_step

STACK = """
import warnings

import numpy as np
import pandas as pd
import patsy
import pyarrow as pa
import scipy.stats as st
import statsmodels.api as sm
import statsmodels.formula.api as smf
from pandas.util._exceptions import find_stack_level


def estimate(df, ctx):
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        warnings.warn("pandas style", UserWarning, stacklevel=find_stack_level())
        warnings.warn("plain", UserWarning, stacklevel=2)
        table = pa.Table.from_pandas(df)
        frame = table.to_pandas()
        design = patsy.dmatrix("x", frame)
        fit = smf.ols("y ~ x", data=frame).fit()
        fit.summary()
        sm.OLS(frame["y"], design).fit()
        test = st.ttest_1samp(np.asarray(frame["y"]), 1.0)
    assert len(caught) >= 3, [str(item.message) for item in caught]
    return {
        "estimate": float(fit.params["x"]),
        "ci_low": float(fit.conf_int().loc["x", 0]),
        "ci_high": float(fit.conf_int().loc["x", 1]),
        "p_value": float(test.pvalue),
        "n": int(len(pd.DataFrame(frame))),
    }
"""

INSPECT = """
import os
import sys

POLICY = %r
SOURCE = %r
START = SOURCE.index("def _borges_install_policy")
SCRIPT = SOURCE[:START] + SOURCE[START:].replace(
    "    sys.addaudithook(hook)", "    return hook, refuse"
).replace("_borges_install_policy(None, None)\\ndel _borges_install_policy", "")
namespace = {}
exec(compile(SCRIPT, "<inspect>", "exec"), namespace)
hook, refuse = namespace["_borges_install_policy"](None, None)
"""

WALK = """
import dis
import types

FORBIDDEN = {
    "LOAD_GLOBAL", "LOAD_NAME", "STORE_GLOBAL", "STORE_NAME", "DELETE_GLOBAL", "DELETE_NAME",
    "LOAD_DEREF", "STORE_DEREF", "LOAD_CLOSURE", "COPY_FREE_VARS", "MAKE_CELL", "IMPORT_NAME",
    "LOAD_FROM_DICT_OR_GLOBALS", "LOAD_FROM_DICT_OR_DEREF",
}
seen, pending, problems = set(), [hook, refuse], []
while pending:
    fn = pending.pop()
    if id(fn) in seen:
        continue
    seen.add(id(fn))
    if fn.__closure__ is not None:
        problems.append(fn.__name__ + " has a closure")
    if fn.__kwdefaults__:
        problems.append(fn.__name__ + " has keyword defaults")
    codes = [fn.__code__]
    while codes:
        code = codes.pop()
        for ins in dis.get_instructions(code):
            if ins.opname in FORBIDDEN:
                problems.append(fn.__name__ + " uses " + ins.opname + " " + str(ins.argval))
        codes.extend(c for c in code.co_consts if isinstance(c, types.CodeType))
    for default in fn.__defaults__ or ():
        if isinstance(default, types.FunctionType):
            pending.append(default)
print(json.dumps({"problems": problems, "functions": len(seen)}))
"""


@pytest.fixture
def backend(tmp_path: Path) -> LocalBackend:
    return LocalBackend(tmp_path / "sandbox")


async def test_numerical_stack_runs_an_ols_with_warnings_under_the_policy(
    backend: LocalBackend,
) -> None:
    result, error = await run_step(backend, STACK, "model")
    assert result.exit_code == 0, (result.stdout, result.stderr, error)
    assert "BORGES_RESULT" in result.stdout


def test_policy_functions_hold_no_cells_globals_or_keyword_defaults() -> None:
    source = harness._POLICY_SOURCE
    script = "import json\n" + INSPECT % ("", source) + WALK
    done = subprocess.run(
        [sys.executable, "-c", script], capture_output=True, text=True, timeout=60, check=False
    )
    assert done.returncode == 0, done.stderr
    report = json.loads(done.stdout.strip().splitlines()[-1])
    assert report["problems"] == [], report["problems"]
    assert report["functions"] >= 12
