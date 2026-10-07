from __future__ import annotations

import pytest

from borges.analysis.code_guard import check_code

VALID_APPLY = """
import pandas as pd
import numpy as np


def apply(df, ctx):
    ctx["n"] = int(len(df))
    return df[df["x"] > 0].copy()
"""

VALID_ESTIMATE = '''
"""Model."""
import statsmodels.api as sm
import statsmodels.formula.api as smf
from scipy import stats
from scipy.stats import norm


def estimate(df, ctx):
    import math
    fit = smf.ols("y ~ x", data=df).fit()
    return {"estimate": float(fit.params["x"]), "n": len(df), "p_value": 0.5,
            "ci_low": 0.0, "ci_high": 1.0, "extra": {"s": math.sqrt(2)}}
'''


def wrap(body: str) -> str:
    return "def apply(df, ctx):\n" + "\n".join("    " + line for line in body.splitlines())


def test_valid_apply_accepted() -> None:
    assert check_code(VALID_APPLY, "filter") == []


def test_valid_estimate_accepted() -> None:
    assert check_code(VALID_ESTIMATE, "model") == []


def test_syntax_error() -> None:
    assert "syntax error" in check_code("def apply(df, ctx:", "filter")[0]


def test_reject_os_import_top_level() -> None:
    assert check_code("import os\n" + VALID_APPLY, "filter")


def test_reject_os_import_inside() -> None:
    assert check_code(wrap("import os\nreturn df"), "filter")


def test_reject_from_import_forbidden() -> None:
    assert check_code("from os import path\n" + VALID_APPLY, "filter")


def test_reject_relative_import() -> None:
    assert check_code("from . import x\n" + VALID_APPLY, "filter")


def test_reject_open() -> None:
    assert check_code(wrap("open('f')\nreturn df"), "filter")


@pytest.mark.parametrize("name", ["eval", "exec", "compile", "getattr", "globals", "input"])
def test_reject_forbidden_names(name: str) -> None:
    assert check_code(wrap(f"{name}('x')\nreturn df"), "filter")


def test_reject_to_csv() -> None:
    assert check_code(wrap("df.to_csv('a.csv')\nreturn df"), "filter")


def test_reject_read_csv() -> None:
    assert check_code("import pandas as pd\n" + wrap("return pd.read_csv('a.csv')"), "filter")


def test_allow_to_numpy_and_friends() -> None:
    body = "a = df['x'].to_numpy()\nb = df.to_dict()\nreturn df"
    assert check_code(wrap(body), "filter") == []


def test_reject_dunder_attribute() -> None:
    assert check_code(wrap("x = df.__class__\nreturn df"), "filter")


def test_reject_dunder_name() -> None:
    assert check_code(wrap("x = __builtins__\nreturn df"), "filter")


def test_reject_forbidden_module_name() -> None:
    assert check_code(wrap("sys.exit(1)\nreturn df"), "filter")


def test_reject_second_top_level_statement() -> None:
    assert check_code(VALID_APPLY + "\nx = 1\n", "filter")


def test_reject_two_functions() -> None:
    assert check_code(VALID_APPLY + "\n\ndef other(df, ctx):\n    return df\n", "filter")


def test_reject_wrong_name_for_kind() -> None:
    assert check_code(VALID_APPLY, "model")
    assert check_code(VALID_ESTIMATE, "transform")


def test_reject_wrong_params() -> None:
    assert check_code("def apply(df):\n    return df\n", "filter")


def test_reject_no_function() -> None:
    assert check_code("import pandas as pd\n", "filter")


def test_print_allowed() -> None:
    assert check_code(wrap("print('hi')\nreturn df"), "filter") == []


@pytest.mark.parametrize(
    "header",
    [
        "from pandas import read_csv",
        "from numpy import load",
        "from numpy import memmap",
        "from pandas.io.common import os as o",
        "from pandas.io import common",
        "import scipy.io",
        "import numpy.lib",
        "from os import path",
        "from numpy import *",
    ],
)
def test_reject_import_escapes(header: str) -> None:
    assert check_code(header + "\n" + VALID_APPLY, "filter")


@pytest.mark.parametrize(
    "body",
    [
        "np.DataSource().open('/etc/passwd')\nreturn df",
        "np.memmap('/etc/passwd')\nreturn df",
        "raise SystemExit(0)",
        "np.testing.runstring('import os', {})\nreturn df",
        "t = np.testing\nt.measure('1 + 1')\nreturn df",
        "f = np.testing.rundocs\nreturn df",
    ],
)
def test_reject_attribute_and_exit_escapes(body: str) -> None:
    assert check_code("import numpy as np\n" + wrap(body), "filter")


def test_allowed_from_imports_still_pass() -> None:
    code = "from scipy import stats\nfrom math import sqrt\n" + VALID_APPLY
    assert check_code(code, "filter") == []


def test_the_sandwich_covariance_module_sm_stats_already_exposes_is_allowed() -> None:
    code = "from statsmodels.stats.sandwich_covariance import cov_cluster\n" + VALID_APPLY
    assert check_code(code, "filter") == []


def test_the_proportion_module_for_wilson_intervals_is_allowed() -> None:
    code = "from statsmodels.stats.proportion import proportion_confint\n" + VALID_APPLY
    assert check_code(code, "filter") == []


@pytest.mark.parametrize(
    "body",
    [
        "pd.eval(\"pd.read_csv('/x', sep='@@@')\", engine='python')\nreturn df",
        "df.eval('@pd.io.common.os.popen(1).read()', engine='python')\nreturn df",
        "return df.query('x > 0')",
        "return df.query('@pd.io.common.os.popen(1)')",
        "'{0.__class__}'.format(df)\nreturn df",
        "'{0}'.format_map(df)\nreturn df",
        "df.to_numpy().dump('/x')\nreturn df",
        "np.ndarray.dumps(df)\nreturn df",
        "scipy.sparse.save_npz('/x', m)\nreturn df",
        "scipy.sparse.load_npz('/x')\nreturn df",
        "statsmodels.datasets.get_rdataset('x')\nreturn df",
        "statsmodels.iolib.foo\nreturn df",
        "pd.HDFStore('/x')\nreturn df",
        "pd.ExcelFile('/x')\nreturn df",
        "pd.ExcelWriter('/x')\nreturn df",
        "sm.datasets.webuse('x')\nreturn df",
        "x = 'a__b'\nreturn df",
        "x = 'a@b'\nreturn df",
    ],
)
def test_reject_eval_io_and_string_bypasses(body: str) -> None:
    assert check_code(wrap(body), "filter")


def test_plain_strings_still_accepted() -> None:
    assert check_code(wrap("x = 'plain text'\nreturn df[df['a'] > 0]"), "filter") == []


@pytest.mark.parametrize(
    "body",
    [
        "np.savez_compressed('/tmp/x', a=df['x'].to_numpy())\nreturn df",
        "np.save_anything('/tmp/x')\nreturn df",
    ],
)
def test_reject_numpy_save_variants(body: str) -> None:
    assert check_code(wrap(body), "filter")


@pytest.mark.parametrize(
    "formula",
    [
        "y ~ I(len(open('/etc/hosts').read()) + x)",
        "y ~ I(len(open(x)))",
        "y ~ I(eval(x))",
        "y ~ system(x)",
    ],
)
def test_reject_formula_code_execution(formula: str) -> None:
    code = (
        "import statsmodels.formula.api as smf\n\n\n"
        "def estimate(df, ctx):\n"
        f'    return smf.ols("{formula}", df).fit()\n'
    )
    assert check_code(code, "model")


def test_reject_split_formula_call() -> None:
    code = (
        "import statsmodels.formula.api as smf\n\n\n"
        "def estimate(df, ctx):\n"
        '    return smf.ols("y ~ I(" + "len(open(x)))", df).fit()\n'
    )
    assert check_code(code, "model")


def estimate_code(body: str) -> str:
    return f"import statsmodels.formula.api as smf\n\n\ndef estimate(df, ctx):\n{body}\n"


@pytest.mark.parametrize(
    "body",
    [
        "    if t.startswith('C(') and t.endswith(', drop_first=True)'):\n        return 1",
        "    if t.startswith(('C(', 'np.log(')) or 'I(' in t:\n        return 1",
        '    f = "y ~ x + C(g) + " + " + ".join(ctx["covariates"])\n    return f',
    ],
)
def test_accept_constants_that_are_probes_or_end_in_an_operator(body: str) -> None:
    assert check_code(estimate_code(body), "model") == []


@pytest.mark.parametrize(
    "body",
    [
        '    return "y ~ I(x + "',
        "    p = 'C('\n    return t.startswith(p)",
        '    return "y ~ x + os.system(1) + "',
        "    return t.startswith('__')",
    ],
)
def test_refuse_open_calls_outside_probes(body: str) -> None:
    assert check_code(estimate_code(body), "model")


def test_accept_plain_formulas() -> None:
    code = (
        "import statsmodels.formula.api as smf\n\n\n"
        "def estimate(df, ctx):\n"
        '    return smf.ols("y ~ x + I(x ** 2) + C(g) + np.log(z)", df).fit()\n'
    )
    assert check_code(code, "model") == []


def model_code(body: str) -> str:
    return (
        "import statsmodels.formula.api as smf\nimport pandas as pd\n\n\n"
        f"def estimate(df, ctx):\n{body}\n"
    )


@pytest.mark.parametrize(
    "body",
    [
        '    f = "y ~ x" + " + I(len(pd.io.common.os.getcwd()))"\n    return smf.ols(f, df).fit()',
        '    f = "y ~ x" + " + I(len(pd.io.common.os.popen(1)))"\n    return smf.ols(f, df).fit()',
        '    f = "y ~ x + I(pd.io.common.os.system(x))"\n    return smf.ols(f, df).fit()',
        '    f = "y ~ x" + " + I(pd.io.common.os.getcwd())"\n    return smf.ols(f, df).fit()',
        '    f = "y ~ I(" + "x)"\n    return smf.ols(f, df).fit()',
        '    f = "("\n    return smf.ols(f, df).fit()',
        '    f = "y ~ x + I(x"\n    return smf.ols(f, df).fit()',
        '    f = "pd.io.common.os.getcwd"\n    return smf.ols(f, df).fit()',
        '    f = "np.log"\n    return smf.ols(f, df).fit()',
        '    f = "y ~ np.linalg.norm(x)"\n    return smf.ols(f, df).fit()',
        '    f = "y ~ " + "pd" + "." + "io" + "." + "common.os.getcwd" + "(x)"\n    return 1',
        '    f = "y ~ x + len(x)"\n    return smf.ols(f, df).fit()',
        '    f = "y ~ I(open(x))"\n    return smf.ols(f, df).fit()',
        '    f = "see os.path"\n    return 1',
    ],
)
def test_reject_formula_string_bypasses(body: str) -> None:
    assert check_code(model_code(body), "model")


def test_jury_split_string_script_is_rejected() -> None:
    body = (
        '    f = "y ~ x" + " + I(len(pd.io.common.os.getcwd()))"\n    return smf.ols(f, df).fit()'
    )
    problems = check_code(model_code(body), "model")
    assert any("string constant rejected" in p for p in problems)


@pytest.mark.parametrize(
    "formula",
    [
        "y ~ x + I(x ** 2) + C(g) + np.log(z)",
        "y ~ C(country) + standardize(x) + center(z)",
        "y ~ np.log1p(a) * np.sqrt(b) : np.abs(c) - 1",
        "y ~ I((a + b) / 2) + poly(x, 3) + bs(x, df=4)",
        "~x",
        "y ~ x | g",
        "converted ~ treatment + C(platform)",
        " + C(country)",
        "plain prose without anything special",
        "Pr(>|z|)",
    ],
)
def test_accept_legitimate_formulas(formula: str) -> None:
    body = f'    f = "{formula}"\n    return smf.ols(f, df).fit()'
    assert check_code(model_code(body), "model") == []


def test_accept_formula_built_from_terms() -> None:
    body = (
        '    terms = ["a", "b"]\n    f = "y ~ " + " + ".join(terms) + " + C(country)"\n'
        "    return smf.ols(f, df).fit()"
    )
    assert check_code(model_code(body), "model") == []


def test_rejection_is_audited_with_hash_not_code(tmp_path) -> None:
    from borges.config import Settings
    from borges.telemetry import hooks
    from borges.telemetry.audit_verify import read_records
    from borges.telemetry.caller import calling_as
    from borges.telemetry.run_telemetry import RunTelemetry

    telemetry = RunTelemetry.open(
        Settings(_env_file=None, borges_home=tmp_path / "home"), "r1", tmp_path / "run"
    )
    bad = "import os\n\n\ndef apply(df, ctx):\n    return df\n"
    with hooks.bound(telemetry), telemetry.span("run", "run r1"):
        with calling_as(step_id="s1", option_id="a"):
            assert check_code(bad, "filter")
        assert check_code(VALID_APPLY, "filter") == []
    telemetry.close()
    (record,) = read_records(tmp_path / "run" / "audit.jsonl")
    assert record.kind == "policy.code_guard" and record.decision == "deny"
    assert record.data["step_id"] == "s1" and record.data["option_id"] == "a"
    assert len(record.data["code_sha256"]) == 64 and "import os\n" not in str(record.data)
