from __future__ import annotations

import os

import pytest

from borges.config import Settings
from borges.sandbox.factory import make_backend

KEY = os.environ.get("CONTREE_API_KEY") or os.environ.get("NEBIUS_API_KEY")
PROJECT = os.environ.get("CONTREE_PROJECT_ID") or os.environ.get("NEBIUS_PROJECT_ID")

pytestmark = [
    pytest.mark.live,
    pytest.mark.skipif(
        not (KEY and PROJECT),
        reason="NEBIUS_API_KEY and NEBIUS_PROJECT_ID are required",
    ),
]


async def test_branching_roundtrip() -> None:
    backend = make_backend(Settings(_env_file=None), "contree")  # type: ignore[call-arg]
    root = await backend.root({"a.txt": b"hello"})
    a = await backend.run(root, ["python", "-c", "open('x','w').write('a')"])
    b = await backend.run(root, ["python", "-c", "open('x','w').write('b')"])
    assert a.ok and b.ok
    assert await backend.read_file(a.checkpoint, "x") == b"a"
    assert await backend.read_file(b.checkpoint, "x") == b"b"
    assert await backend.read_file(root, "a.txt") == b"hello"
    check = await backend.run(root, ["python", "-c", "import pandas, statsmodels"])
    assert check.ok, check.stderr
    await backend.close()
