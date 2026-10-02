from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from borges.sandbox.backend import Checkpoint, SandboxError
from borges.sandbox.contree_backend import ContreeBackend, _remote_path


class FakeImage:
    def __init__(self, uuid: str | None, store: FakeStore, files: dict[str, bytes] | None = None):
        self.uuid = uuid
        self.store = store
        self.files = dict(files or {})
        self.result: Any = None

    def run(self, **kwargs: Any) -> FakeRun:
        return FakeRun(self, kwargs)

    async def read(self, path: str) -> bytes:
        if path not in self.files:
            raise KeyError(path)
        return self.files[path]


class FakeRun:
    def __init__(self, image: FakeImage, kwargs: dict[str, Any]) -> None:
        self.image = image
        self.kwargs = kwargs

    def __await__(self):
        return self._exec().__await__()

    async def _exec(self) -> FakeImage:
        store = self.image.store
        store.calls.append(self.kwargs)
        child = FakeImage(f"uuid-{len(store.calls)}", store, self.image.files)
        child.files.update(self.kwargs.get("files") or {})
        code = 3 if self.kwargs.get("command") == "fail" else 0
        child.result = SimpleNamespace(exit_code=code, stdout="out", stderr=b"err")
        return child


class FakeStore:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []


class FakeImages:
    def __init__(self, store: FakeStore) -> None:
        self.store = store
        self.used: list[str] = []

    async def use(self, ref: str, strict: bool = False) -> FakeImage:
        self.used.append(ref)
        return FakeImage(ref, self.store)


@pytest.fixture
def backend() -> ContreeBackend:
    instance = ContreeBackend("key", "https://example.invalid")
    store = FakeStore()
    instance._client = SimpleNamespace(images=FakeImages(store))
    instance._runner = FakeImage("runner", store)
    return instance


async def test_root_uploads_under_workdir(backend: ContreeBackend) -> None:
    root = await backend.root({"data/a.csv": b"1,2"})
    assert root == Checkpoint("uuid-1", None, "contree")
    call = backend._runner.store.calls[0]
    assert call["files"] == {"/borges/data/a.csv": b"1,2"}
    assert call["disposable"] is False


async def test_run_maps_result(backend: ContreeBackend) -> None:
    root = await backend.root({})
    result = await backend.run(root, ["python", "-c", "pass"], {"s.py": b"x"}, timeout_s=7)
    call = backend._runner.store.calls[-1]
    assert call["command"] == "python"
    assert call["args"] == ["-c", "pass"]
    assert call["cwd"] == "/borges"
    assert call["timeout"] == 7
    assert call["disposable"] is False
    assert call["files"] == {"/borges/s.py": b"x"}
    assert result.checkpoint.parent_id == root.id
    assert result.checkpoint.backend == "contree"
    assert (result.exit_code, result.stdout, result.stderr) == (0, "out", "err")


async def test_failed_run_keeps_checkpoint(backend: ContreeBackend) -> None:
    root = await backend.root({})
    result = await backend.run(root, ["fail"])
    assert result.exit_code == 3 and not result.ok
    assert result.checkpoint.id != root.id


async def test_read_file_and_fallback_to_use(backend: ContreeBackend) -> None:
    root = await backend.root({"a.txt": b"a"})
    assert await backend.read_file(root, "a.txt") == b"a"
    unknown = Checkpoint("elsewhere", None, "contree")
    with pytest.raises(KeyError):
        await backend.read_file(unknown, "a.txt")
    assert backend._client.images.used == ["elsewhere"]


async def test_read_file_rejects_traversal(backend: ContreeBackend) -> None:
    root = await backend.root({})
    with pytest.raises(SandboxError, match="escapes"):
        await backend.read_file(root, "../etc/passwd")


def test_remote_path() -> None:
    assert _remote_path("a/./b.txt") == "/borges/a/b.txt"
    assert _remote_path("a/../b.txt") == "/borges/b.txt"
    with pytest.raises(SandboxError):
        _remote_path("/etc/passwd")


class BuildImage:
    def __init__(self, log: list[tuple[str, Any]], exit_code: int = 0, stderr: str = "") -> None:
        self.log = log
        self.result = SimpleNamespace(exit_code=exit_code, stdout="", stderr=stderr)
        self.uuid = "built"

    def run(self, **kwargs: Any) -> Any:
        self.log.append(("run", kwargs))
        outcome = self.log_outcomes.pop(0)
        return _Done(outcome)

    async def tag_as(self, tag: str) -> BuildImage:
        self.log.append(("tag", tag))
        return self


class _Done:
    def __init__(self, image: Any) -> None:
        self.image = image

    def __await__(self):
        async def go() -> Any:
            return self.image

        return go().__await__()


class BuildImages:
    def __init__(self, base: BuildImage) -> None:
        self.base = base

    async def use(self, ref: str, strict: bool = False) -> Any:
        from contree_sdk.sdk.exceptions import NotFoundError

        raise NotFoundError("missing")

    async def oci(self, ref: str) -> BuildImage:
        return self.base


def _builder(outcomes: list[BuildImage]) -> tuple[ContreeBackend, list[tuple[str, Any]]]:
    log: list[tuple[str, Any]] = []
    base = BuildImage(log)
    base.log_outcomes = outcomes
    for image in outcomes:
        image.log = log
        image.log_outcomes = outcomes
    backend = ContreeBackend("key", "https://example.invalid")
    backend._client = SimpleNamespace(images=BuildImages(base))
    return backend, log


async def test_runner_image_is_tagged_only_after_install_and_import_check() -> None:
    backend, log = _builder([BuildImage([]), BuildImage([])])
    await backend.ensure_runner_image()
    runs = [entry for kind, entry in log if kind == "run"]
    assert "pip install" in runs[0]["shell"] and "tag" not in runs[0]
    assert "import pandas, numpy, scipy, statsmodels, pyarrow" in runs[1]["shell"]
    assert [kind for kind, _ in log] == ["run", "run", "tag"]


async def test_failed_install_is_not_tagged() -> None:
    backend, log = _builder([BuildImage([], exit_code=1, stderr="ERROR: no matching distribution")])
    with pytest.raises(SandboxError, match="no matching distribution"):
        await backend.ensure_runner_image()
    assert not any(kind == "tag" for kind, _ in log)


async def test_failed_import_check_is_not_tagged() -> None:
    backend, log = _builder(
        [BuildImage([]), BuildImage([], exit_code=1, stderr="ImportError: pyarrow")]
    )
    with pytest.raises(SandboxError, match="ImportError: pyarrow"):
        await backend.ensure_runner_image()
    assert not any(kind == "tag" for kind, _ in log)


def test_project_id_reaches_the_auth_config() -> None:
    backend = ContreeBackend("key", "https://example.invalid", project_id="proj-123")
    assert backend._client.config.auth.get_headers()["Project"] == "proj-123"
