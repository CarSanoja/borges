from __future__ import annotations

import os

import pytest

from borges.sandbox.contree_backend import ContreeBackend

pytestmark = [
    pytest.mark.live,
    pytest.mark.skipif(
        not (os.environ.get("CONTREE_API_KEY") and os.environ.get("CONTREE_BASE_URL")),
        reason="CONTREE_API_KEY and CONTREE_BASE_URL are required",
    ),
]


async def test_branching_roundtrip() -> None:
    backend = ContreeBackend(os.environ["CONTREE_API_KEY"], os.environ["CONTREE_BASE_URL"])
    root = await backend.root({"a.txt": b"hello"})
    a = await backend.run(root, ["python", "-c", "open('x','w').write('a')"])
    b = await backend.run(root, ["python", "-c", "open('x','w').write('b')"])
    assert a.ok and b.ok
    assert await backend.read_file(a.checkpoint, "x") == b"a"
    assert await backend.read_file(b.checkpoint, "x") == b"b"
    assert await backend.read_file(root, "a.txt") == b"hello"
    check = await backend.run(root, ["python", "-c", "import pandas, statsmodels"])
    assert check.ok, check.stderr
