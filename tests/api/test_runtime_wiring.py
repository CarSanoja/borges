from __future__ import annotations

import pytest
from fastapi import HTTPException

from borges.api.app import create_app
from borges.api.runtime_wiring import attach_runtime, get_runtime, require_runtime
from borges.config import Settings
from borges.runs.bus import EventBus
from borges.runs.store import RunStore


class Request:
    def __init__(self, app) -> None:
        self.app = app


def test_a_real_orchestrator_gets_a_runtime(tmp_path) -> None:
    app = create_app(settings=Settings(_env_file=None, borges_home=tmp_path))
    assert app.state.runtime is None
    from borges.api.app import _build_missing

    _build_missing(app)
    runtime = attach_runtime(app)
    assert runtime is not None and attach_runtime(app) is runtime
    assert get_runtime(Request(app)) is runtime and require_runtime(Request(app)) is runtime


def test_a_stand_in_orchestrator_gets_none(tmp_path) -> None:
    store = RunStore(tmp_path / "runs")
    app = create_app(
        settings=Settings(_env_file=None, borges_home=tmp_path),
        orchestrator=object(),
        registry=object(),
        store=store,
        bus=EventBus(store),
    )
    assert attach_runtime(app) is None and get_runtime(Request(app)) is None
    with pytest.raises(HTTPException) as refused:
        require_runtime(Request(app))
    assert refused.value.status_code == 503
