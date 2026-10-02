from __future__ import annotations

from borges.runtime.alias_backend import AliasBackend
from borges.sandbox.backend import Checkpoint, ExecResult


class Inner:
    name = "inner"

    def __init__(self) -> None:
        self.seen: list[str] = []

    async def root(self, files):
        return Checkpoint("real_root", None, self.name)

    async def run(self, parent, command, files=None, timeout_s=120.0):
        self.seen.append(parent.id)
        child = Checkpoint(f"child_of_{parent.id}", parent.id, self.name)
        return ExecResult(child, 0, "", "", 0.1)

    async def read_file(self, checkpoint, path):
        self.seen.append(checkpoint.id)
        return b"data"

    async def close(self) -> None:
        return None


async def test_known_ids_resolve_to_the_rebuilt_checkpoint() -> None:
    inner = Inner()
    backend = AliasBackend(inner)
    backend.aliases["old_root"] = await inner.root({})
    result = await backend.run(Checkpoint("old_root", None, "inner"), ["python"])
    assert inner.seen == ["real_root"]
    assert result.checkpoint.id == "child_of_real_root"
    assert result.checkpoint.parent_id == "old_root"
    assert await backend.read_file(Checkpoint("old_root", None, "inner"), "f") == b"data"
    assert inner.seen[-1] == "real_root"


async def test_unknown_ids_pass_through() -> None:
    inner = Inner()
    backend = AliasBackend(inner)
    result = await backend.run(Checkpoint("fresh", None, "inner"), ["python"])
    assert inner.seen == ["fresh"] and result.checkpoint.parent_id == "fresh"
    assert backend.name == "inner"
    assert (await backend.root({})).id == "real_root"
    await backend.close()
