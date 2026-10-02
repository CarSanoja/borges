from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

from borges.sandbox.local_backend import LocalBackend
from tests.sandbox.policy_support import run_step

DENIAL = "PermissionError: runtime policy denied open for reading"
SECRET = b"NEBIUS_API_KEY=decoy"


def body(statement: str) -> str:
    return f"import os\n\n\ndef apply(df, ctx):\n    {statement}\n    return df\n"


@pytest.fixture
def backend(tmp_path: Path) -> LocalBackend:
    return LocalBackend(tmp_path / "sandbox")


async def assert_denied(
    backend: LocalBackend, statement: str, denial: str = DENIAL, **kwargs: object
) -> str:
    result, error = await run_step(backend, body(statement), **kwargs)
    assert result.exit_code != 0, (result.stdout, result.stderr)
    assert error is not None
    assert denial in error
    assert "decoy" not in error
    return error


async def test_env_file_in_working_directory_is_denied(backend: LocalBackend) -> None:
    files = {".env": SECRET, ".env.local": SECRET}
    await assert_denied(backend, "print(open('.env').read())", root_files=files)
    await assert_denied(backend, "print(open('.env.local').read())", root_files=files)


async def test_env_file_next_to_working_directory_is_denied(
    backend: LocalBackend, tmp_path: Path
) -> None:
    (tmp_path / "sandbox").mkdir(exist_ok=True)
    (tmp_path / "sandbox" / ".env").write_bytes(SECRET)
    statement = "print(open(os.path.join(os.getcwd(), '..', '..', '..', '.env')).read())"
    await assert_denied(backend, statement)


async def test_env_file_inside_an_allowed_root_is_denied(backend: LocalBackend) -> None:
    statement = "print(open(os.path.join(os.path.dirname(os.__file__), '.env')).read())"
    await assert_denied(backend, statement)


async def test_symlink_to_env_file_is_denied(backend: LocalBackend, tmp_path: Path) -> None:
    target = tmp_path / ".env"
    target.write_bytes(SECRET)
    statement = f"os.symlink({str(target)!r}, 'link.txt'); open('link.txt').read()"
    await assert_denied(backend, statement)
    await assert_denied(backend, f"open({str(target)!r}).read()")


async def test_files_under_the_home_root_are_denied(backend: LocalBackend, tmp_path: Path) -> None:
    home = tmp_path / "home"
    (home / ".ssh").mkdir(parents=True)
    (home / ".ssh" / "id_rsa").write_bytes(SECRET)
    (home / "notes.txt").write_bytes(SECRET)
    for name in (".ssh/id_rsa", "notes.txt"):
        await assert_denied(backend, f"open({str(home / name)!r}).read()", policy_home=str(home))
    await assert_denied(
        backend,
        f"os.listdir({str(home / '.ssh')!r})",
        policy_home=str(home),
        denial="runtime policy denied os.listdir",
    )


async def test_listing_outside_the_allowlist_is_denied(backend: LocalBackend) -> None:
    result, error = await run_step(backend, body("os.listdir('/')"))
    assert result.exit_code != 0
    assert error is not None
    assert "runtime policy denied os.listdir" in error
    result, error = await run_step(backend, body("list(os.scandir('/'))"))
    assert error is not None
    assert "runtime policy denied os.scandir" in error


@pytest.mark.parametrize(
    "path",
    [
        "/proc/1/environ",
        "/proc/self/environ",
        "/proc/thread-self/environ",
        "/proc/self/../1/environ",
        "/proc/2/cmdline",
        "/proc/self/mem",
        "/proc/self/maps",
        "/proc/self/root/proc/1/environ",
    ],
)
async def test_proc_secrets_are_denied_by_path(backend: LocalBackend, path: str) -> None:
    await assert_denied(backend, f"open({path!r}, 'rb').read()")


@pytest.mark.skipif(not sys.platform.startswith("linux"), reason="needs /proc")
async def test_parent_process_environment_is_denied(
    backend: LocalBackend, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("BORGES_DECOY_SECRET", "decoy")
    await assert_denied(backend, f"open('/proc/{os.getpid()}/environ', 'rb').read()")


async def test_data_and_working_directory_stay_usable(backend: LocalBackend) -> None:
    statement = (
        "import pandas as pd; pd.read_parquet('data.parquet'); "
        "open('out.txt', 'w').write('ok'); assert open('out.txt').read() == 'ok'; "
        "assert os.listdir('.')"
    )
    result, error = await run_step(backend, body(statement))
    assert result.exit_code == 0, (result.stdout, result.stderr, error)


async def test_numerical_stack_runs_an_ols_under_the_policy(backend: LocalBackend) -> None:
    code = (
        "import numpy as np\nimport pandas as pd\nimport patsy\nimport pyarrow as pa\n"
        "import scipy.stats as st\nimport statsmodels.api as sm\n"
        "import statsmodels.formula.api as smf\n\n\n"
        "def apply(df, ctx):\n"
        "    patsy.dmatrix('x', df)\n"
        "    pa.Table.from_pandas(df)\n"
        "    st.ttest_ind(df.x, df.y)\n"
        "    fit = smf.ols('y ~ x', data=df).fit()\n"
        "    sm.OLS(df.y, sm.add_constant(df.x)).fit()\n"
        "    ctx['slope'] = float(np.round(fit.params['x'], 3))\n"
        "    return df\n"
    )
    result, error = await run_step(backend, code)
    assert result.exit_code == 0, (result.stdout, result.stderr, error)


async def test_audit_mode_logs_denied_reads_and_allows_them(
    backend: LocalBackend, tmp_path: Path
) -> None:
    log = tmp_path / "audit.log"
    result, error = await run_step(
        backend, body("open('/etc/hosts').read()"), policy_audit_path=str(log)
    )
    assert result.exit_code == 0, (result.stdout, result.stderr, error)
    assert "/etc/hosts" in log.read_text()


async def test_audit_mode_is_off_by_default(backend: LocalBackend, tmp_path: Path) -> None:
    result, _ = await run_step(backend, body("open('/etc/hosts').read()"))
    assert result.exit_code != 0
