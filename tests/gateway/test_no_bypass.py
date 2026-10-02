from __future__ import annotations

import ast
import contextlib
from pathlib import Path

from borges.cases.registry import CaseRegistry
from borges.config import REPO_ROOT
from borges.gateway.guard import inside_gateway
from borges.llm.factory import make_llm
from borges.runs.bus import EventBus
from borges.runs.models import RunRequest
from borges.runs.orchestrator import RunOrchestrator
from borges.runs.store import RunStore
from borges.sandbox.factory import make_backend
from borges.telemetry.audit_verify import read_records
from borges.telemetry.run_telemetry import run_audit_path
from tests.telemetry.conftest import make_settings

SRC = REPO_ROOT / "src" / "borges"

CONSTRUCTORS = {
    "NebiusLLM": {"llm/factory.py"},
    "ScriptedLLM": {"llm/factory.py"},
    "AsyncOpenAI": {"llm/nebius_provider.py"},
    "ContreeBackend": {"sandbox/factory.py"},
    "LocalBackend": {"sandbox/factory.py"},
    "make_llm": set(),
    "make_backend": {"cli_runtime.py"},
}


def called_names(path: Path) -> list[tuple[str, int]]:
    found = []
    for node in ast.walk(ast.parse(path.read_text())):
        if isinstance(node, ast.Call):
            func = node.func
            name = func.id if isinstance(func, ast.Name) else getattr(func, "attr", None)
            if name:
                found.append((name, node.lineno))
    return found


def test_providers_are_only_constructed_inside_the_factories() -> None:
    offenders = []
    for path in sorted(SRC.rglob("*.py")):
        relative = path.relative_to(SRC).as_posix()
        for name, line in called_names(path):
            if name in CONSTRUCTORS and relative not in CONSTRUCTORS[name]:
                offenders.append(f"{relative}:{line} calls {name}")
    assert not offenders, offenders


def test_the_openai_sdk_is_imported_only_by_the_provider() -> None:
    offenders = []
    for path in sorted(SRC.rglob("*.py")):
        relative = path.relative_to(SRC).as_posix()
        for node in ast.walk(ast.parse(path.read_text())):
            modules = []
            if isinstance(node, ast.Import):
                modules = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                modules = [node.module]
            if any(m.split(".")[0] == "openai" for m in modules) and not relative.startswith(
                "llm/"
            ):
                offenders.append(relative)
    assert not offenders, offenders


def test_the_orchestrator_is_the_only_caller_of_the_llm_factory() -> None:
    callers = {
        path.relative_to(SRC).as_posix()
        for path in SRC.rglob("*.py")
        if any(name == "llm_factory" for name, _ in called_names(path))
    }
    assert callers == {"runs/orchestrator.py"}


class SpyLLM:
    def __init__(self, inner) -> None:
        self.inner = inner
        self.calls: list[bool] = []
        self.totals = inner.totals

    async def complete(self, *args, **kwargs):
        self.calls.append(inside_gateway())
        return await self.inner.complete(*args, **kwargs)


class SpyBackend:
    def __init__(self, inner) -> None:
        self.inner = inner
        self.name = inner.name
        self.calls: list[tuple[str, bool]] = []

    async def root(self, files):
        self.calls.append(("root", inside_gateway()))
        return await self.inner.root(files)

    async def run(self, parent, command, files=None, timeout_s=120.0):
        self.calls.append(("run", inside_gateway()))
        return await self.inner.run(parent, command, files=files, timeout_s=timeout_s)

    async def read_file(self, checkpoint, path):
        self.calls.append(("read_file", inside_gateway()))
        return await self.inner.read_file(checkpoint, path)

    async def close(self) -> None:
        await self.inner.close()


async def test_every_runtime_model_and_sandbox_call_passes_the_gateway(tmp_path: Path) -> None:
    settings = make_settings(tmp_path)
    llms: list[SpyLLM] = []
    backends: list[SpyBackend] = []

    def llm_factory(settings, mode=None, **options):
        spy = SpyLLM(make_llm(settings, mode, **options))
        llms.append(spy)
        return spy

    def backend_factory(settings, kind=None):
        spy = SpyBackend(make_backend(settings, kind))
        backends.append(spy)
        return spy

    store = RunStore(settings.borges_runs_dir)
    runs = RunOrchestrator(
        settings,
        store,
        EventBus(store),
        CaseRegistry(settings.borges_cases_dir),
        llm_factory=llm_factory,
        backend_factory=backend_factory,
    )
    snapshot = await runs.execute("r_nb", RunRequest(case_id="checkout_ab", llm="scripted"))
    assert snapshot.status == "completed" and snapshot.flip.universe_id == "u_4e00fbb461"
    assert llms[0].calls and all(llms[0].calls)
    assert len(backends[0].calls) > 20 and all(inside for _, inside in backends[0].calls)
    records = read_records(run_audit_path(settings, "r_nb"))
    every_call = [r for r in records if r.kind == "model.call"]
    assert len(every_call) == len(llms[0].calls)
    served = [r for r in every_call if r.data.get("outcome") == "ok"]
    assert served and all(r.decision == "allow" and r.data["policy_sha"] for r in served)
    sandbox = [r for r in records if r.kind == "sandbox.exec"]
    assert sandbox and all(
        r.decision == "allow" and r.principal.endswith("/harness") for r in sandbox
    )
    assert not [r for r in records if r.kind == "gateway.deny"]


async def test_calling_a_spy_outside_the_gateway_is_visible_to_the_check() -> None:
    from borges.llm.scripted_provider import ScriptedLLM

    spy = SpyLLM(ScriptedLLM(REPO_ROOT / "cases" / "checkout_ab" / "fixtures"))
    assert inside_gateway() is False
    with contextlib.suppress(Exception):
        await spy.complete(None, [], key="nope")
    assert spy.calls == [False]
