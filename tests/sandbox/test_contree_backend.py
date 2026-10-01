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
