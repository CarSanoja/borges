from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from borges.sandbox.backend import BranchBackend, SandboxError
from borges.sandbox.local_backend import LocalBackend


@pytest.fixture
def backend(tmp_path: Path) -> LocalBackend:
    return LocalBackend(tmp_path)


async def test_satisfies_protocol(backend: LocalBackend) -> None:
    assert isinstance(backend, BranchBackend)
    assert backend.name == "local"


async def test_root_and_run(backend: LocalBackend) -> None:
    root = await backend.root({"data/a.txt": b"hello"})
    assert root.parent_id is None and root.id.startswith("ck_") and len(root.id) == 15
    result = await backend.run(
        root,
        ["python", "-c", "print(open('data/a.txt').read()); open('out.txt','w').write('x')"],
    )
    assert result.ok
    assert result.stdout.strip() == "hello"
    assert result.checkpoint.parent_id == root.id
    assert result.duration_s > 0
    assert await backend.read_file(result.checkpoint, "out.txt") == b"x"
    assert await backend.read_file(result.checkpoint, "data/a.txt") == b"hello"


async def test_failed_run_still_creates_checkpoint(backend: LocalBackend) -> None:
    root = await backend.root({})
    result = await backend.run(root, ["python", "-c", "import sys; sys.exit(3)"])
    assert result.exit_code == 3
    assert result.checkpoint.id != root.id


async def test_siblings_are_isolated_and_parent_unchanged(backend: LocalBackend) -> None:
    root = await backend.root({"base.txt": b"base"})
    a, b = await asyncio.gather(
        backend.run(root, ["python", "-c", "open('x','w').write('a')"]),
        backend.run(root, ["python", "-c", "open('x','w').write('b')"], files={"extra": b"1"}),
    )
    assert await backend.read_file(a.checkpoint, "x") == b"a"
    assert await backend.read_file(b.checkpoint, "x") == b"b"
    assert await backend.read_file(b.checkpoint, "extra") == b"1"
    with pytest.raises(SandboxError):
        await backend.read_file(a.checkpoint, "extra")
    with pytest.raises(SandboxError):
        await backend.read_file(root, "x")
    assert await backend.read_file(root, "base.txt") == b"base"


async def test_heavy_concurrency_from_one_parent(backend: LocalBackend) -> None:
    root = await backend.root({"base.txt": b"base"})
    results = await asyncio.gather(
        *(backend.run(root, ["python", "-c", f"print({i})"]) for i in range(24))
    )
    assert [r.stdout.strip() for r in results] == [str(i) for i in range(24)]
    assert len({r.checkpoint.id for r in results}) == 24


async def test_timeout_kills_process_group(backend: LocalBackend) -> None:
    root = await backend.root({})
    result = await backend.run(root, ["python", "-c", "import time; time.sleep(30)"], timeout_s=0.5)
    assert result.exit_code == 124
    assert "timeout" in result.stderr
    assert result.duration_s < 10


async def test_read_file_rejects_traversal_and_missing(backend: LocalBackend) -> None:
    root = await backend.root({"a.txt": b"a"})
    with pytest.raises(SandboxError, match="escapes"):
        await backend.read_file(root, "../meta.json")
    with pytest.raises(SandboxError, match="escapes"):
        await backend.read_file(root, "/etc/passwd")
    with pytest.raises(SandboxError, match="no such file"):
        await backend.read_file(root, "missing.txt")


async def test_files_cannot_escape(backend: LocalBackend) -> None:
    with pytest.raises(SandboxError, match="escapes"):
        await backend.root({"../evil": b"x"})


async def test_unknown_parent(backend: LocalBackend) -> None:
    root = await backend.root({})
    ghost = type(root)("ck_000000000000", None, "local")
    with pytest.raises(SandboxError, match="unknown checkpoint"):
        await backend.run(ghost, ["python", "-c", "pass"])


async def test_scientific_stack_available(backend: LocalBackend) -> None:
    root = await backend.root({})
    result = await backend.run(root, ["python", "-c", "import pandas, statsmodels"], timeout_s=60)
    assert result.ok, result.stderr


async def test_cleanup_removes_checkpoints(backend: LocalBackend, tmp_path: Path) -> None:
    await backend.root({"a": b"a"})
    assert (tmp_path / "checkpoints").exists()
    backend.cleanup()
    assert not (tmp_path / "checkpoints").exists()
    await backend.close()
