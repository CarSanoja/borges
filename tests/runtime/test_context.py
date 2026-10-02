from __future__ import annotations

import pytest

from borges.runtime.checkpoints import SqliteCheckpointStore
from borges.runtime.context import CancelToken, RunCancelled, RunContext, RunRetry
from borges.runtime.transient import TransientRunError


def test_cancel_token_keeps_the_first_reason() -> None:
    token = CancelToken()
    assert token.is_set() is False and token.reason is None
    token.set("first")
    token.set("second")
    assert token.is_set() and token.reason == "first"


def test_check_raises_once_cancelled(db) -> None:
    context = RunContext("r1", SqliteCheckpointStore(db))
    context.check()
    context.cancel.set("stop")
    with pytest.raises(RunCancelled, match="stop"):
        context.check()


def test_run_cancelled_is_not_an_ordinary_exception() -> None:
    assert not issubclass(RunCancelled, Exception)


def test_save_writes_a_durable_checkpoint(db) -> None:
    store = SqliteCheckpointStore(db)
    RunContext("r1", store).save("k", 7, {"a": 1})
    assert store.load("r1", "k") == {"a": 1}


def test_failed_retries_only_transient_errors_with_attempts_left(db) -> None:
    store = SqliteCheckpointStore(db)
    context = RunContext("r1", store, attempt=1, max_attempts=3)
    assert context.failed(TransientRunError("503")) is True
    assert context.transient_failure is True
    assert context.failed(ValueError("bad")) is False
    assert context.transient_failure is False
    last = RunContext("r1", store, attempt=3, max_attempts=3)
    assert last.failed(TransientRunError("503")) is False
    assert last.transient_failure is True


def test_resumed_follows_the_reason(db) -> None:
    store = SqliteCheckpointStore(db)
    assert RunContext("r", store).resumed is False
    assert RunContext("r", store, resume_reason="restart").resumed is True


def test_run_retry_carries_the_error() -> None:
    assert RunRetry("x").error == "x"
