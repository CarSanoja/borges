from __future__ import annotations

import os
from pathlib import Path

import pytest

from borges.analysis import harness
from borges.sandbox.local_backend import LocalBackend
from tests.sandbox.policy_support import checkpoint_files, make_step, run_step

PROBE = "/tmp/borges_policy_probe"


def probe_absent() -> bool:
    return not os.path.exists(PROBE)


def body(statement: str) -> str:
    return f"import os\n\n\ndef apply(df, ctx):\n    {statement}\n    return df\n"


@pytest.fixture
def backend(tmp_path: Path) -> LocalBackend:
    return LocalBackend(tmp_path)


def test_policy_precedes_generated_code() -> None:
    step, option = make_step("def apply(df, ctx):\n    return df\n")
    rendered = harness.render_step(step, option)
    assert rendered.startswith("exec(compile(")
    assert rendered.index("addaudithook") < rendered.index("def apply")


@pytest.mark.parametrize(
    ("statement", "event"),
    [
        ("os.system('true')", "os.system"),
        ("os.execv('/bin/true', ['true'])", "os.exec"),
        ("os.spawnl(os.P_WAIT, '/bin/true', 'true')", "os.fork"),
        ("os.posix_spawn('/bin/true', ['true'], {})", "os.posix_spawn"),
        ("os.fork()", "os.fork"),
        ("import subprocess; subprocess.run(['true'])", "subprocess.Popen"),
        ("import pty; pty.spawn(['true'])", "pty.spawn"),
        ("import webbrowser; webbrowser.open('http://x')", "webbrowser.open"),
        ("import ctypes; ctypes.CDLL(None)", "ctypes.dlopen"),
        ("import ctypes; ctypes.string_at(0, 1)", "ctypes."),
        ("import cffi", "import cffi"),
        ("open('/tmp/borges_policy_probe', 'w').write('x')", "open for writing"),
        ("os.open('/tmp/borges_policy_probe', os.O_CREAT | os.O_WRONLY)", "open for writing"),
        ("open('/tmp/borges_policy_probe', 'a')", "open for writing"),
        ("os.remove('/tmp/borges_policy_probe')", "os.remove"),
        ("os.rename('data.parquet', '/tmp/borges_policy_probe')", "os.rename"),
        ("os.rmdir('/tmp')", "os.rmdir"),
        ("import shutil; shutil.rmtree('/tmp/borges_policy_dir')", "shutil.rmtree"),
        ("os.chdir('/')", "os.chdir"),
        ("os.chdir('..')", "os.chdir"),
    ],
)
async def test_denied_event(backend: LocalBackend, statement: str, event: str) -> None:
    result, error = await run_step(backend, body(statement))
    assert result.exit_code != 0
    assert error is not None
    assert "PermissionError" in error or event == "import cffi"
    assert "runtime policy denied" in error
    assert event in error
    assert probe_absent()


@pytest.mark.parametrize(
    "statement",
    [
        "import socket; socket.create_connection(('127.0.0.1', 9), timeout=1)",
        "import socket; socket.socket().bind(('127.0.0.1', 0))",
        "import socket; socket.getaddrinfo('example.com', 80)",
        "import socket; socket.socket(type=socket.SOCK_DGRAM).sendto(b'x', ('127.0.0.1', 9))",
        "import urllib.request; urllib.request.urlopen('http://127.0.0.1:9/')",
    ],
)
async def test_network_is_denied(backend: LocalBackend, statement: str) -> None:
    result, error = await run_step(backend, body(statement))
    assert result.exit_code != 0
    assert error is not None
    assert "PermissionError" in error or "URLError" in error
    assert "runtime policy denied socket." in error


async def test_writes_inside_working_directory_still_work(backend: LocalBackend) -> None:
    statement = (
        "open('note.txt', 'w').write('hi'); os.makedirs('sub/deep', exist_ok=True); "
        "open('sub/deep/a.txt', 'a').write('x'); os.rename('note.txt', 'sub/note.txt'); "
        "os.remove('sub/deep/a.txt'); os.chdir('sub'); os.chdir('..')"
    )
    result, error = await run_step(backend, body(statement))
    assert result.exit_code == 0, (result.stdout, result.stderr, error)
    assert "sub/note.txt" in checkpoint_files(backend, result.checkpoint)


async def test_reads_outside_working_directory_stay_allowed(backend: LocalBackend) -> None:
    statement = "ctx['n'] = len(open('/etc/hosts').read()); ctx['l'] = len(os.listdir('/'))"
    result, error = await run_step(backend, body(statement))
    assert result.exit_code == 0, (result.stdout, result.stderr, error)


async def test_library_stack_loads_under_policy(backend: LocalBackend) -> None:
    code = (
        "import numpy, pandas, pyarrow, scipy.stats, statsmodels.api as sm\n"
        "import statsmodels.formula.api as smf\n\n\n"
        "def apply(df, ctx):\n"
        "    smf.ols('y ~ x', data=df).fit()\n"
        "    return df\n"
    )
    result, error = await run_step(backend, code)
    assert result.exit_code == 0, (result.stdout, result.stderr, error)


async def test_late_audit_hook_is_refused(backend: LocalBackend) -> None:
    statement = (
        "import sys; seen = []; sys.addaudithook(lambda e, a: seen.append(e)); "
        "os.listdir('.'); assert not seen, 'hook was registered'"
    )
    result, error = await run_step(backend, body(statement))
    assert result.exit_code == 0, (result.stdout, result.stderr, error)


async def test_tempfiles_land_in_working_directory(backend: LocalBackend) -> None:
    statement = "import tempfile; tempfile.NamedTemporaryFile().close(); ctx['d'] = 1"
    result, error = await run_step(backend, body(statement))
    assert result.exit_code == 0, (result.stdout, result.stderr, error)
