from __future__ import annotations

from typing import Any

import pytest

from borges.analysis import smoke_left_out
from borges.analysis.models import Option, Step
from borges.analysis.smoke_left_out import IDENTITY, leave_out
from borges.gateway.code_evidence import CodeEvidence, collecting


async def test_the_pass_through_is_recorded_as_guarded_before_it_runs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen: list[int] = []
    evidence = CodeEvidence()

    async def execute(*_: Any) -> tuple[None, str, None, None]:
        seen.append(len(evidence))
        return None, "stopped", None, None

    monkeypatch.setattr(smoke_left_out, "execute", execute)
    option = Option(id="w", label="Winsorize", rationale="r", spec="s", is_default=True)
    step = Step(id="clean", title="Clean", kind="filter", description="d", options=[option])
    with collecting(evidence):
        assert await leave_out(object(), step, object(), []) is None
    assert seen == [1]
    assert IDENTITY.rstrip("\n") in evidence._codes.values()
