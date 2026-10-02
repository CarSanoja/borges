from __future__ import annotations

from borges.config import Settings
from borges.runs.models import RunRequest
from borges.runtime.idempotency import (
    EXPLICIT_WINDOW_S,
    derived_key,
    explicit_key,
    schedule_key,
    valid_header,
)


def test_header_validation() -> None:
    assert valid_header("abc-123_x.y:z")
    assert not valid_header("")
    assert not valid_header("a b")
    assert not valid_header("x" * 129)
    assert not valid_header("emoji✓")


def test_explicit_key_is_scoped_to_the_principal() -> None:
    a = explicit_key("caller://alice", "k1")
    assert a == explicit_key("caller://alice", "k1")
    assert a != explicit_key("caller://bob", "k1")
    assert a.derived is False and a.window_s == EXPLICIT_WINDOW_S


def test_derived_key_follows_owner_and_request() -> None:
    settings = Settings(_env_file=None, borges_idempotency_window_s=600)
    request = RunRequest(case_id="checkout_ab", llm="scripted")
    key = derived_key("owner", request, settings)
    assert key.derived is True and key.window_s == 600
    assert key == derived_key("owner", RunRequest(case_id="checkout_ab", llm="scripted"), settings)
    assert key != derived_key("other", request, settings)
    assert key != derived_key("owner", RunRequest(case_id="red_cards", llm="scripted"), settings)


def test_schedule_key_changes_with_the_slot() -> None:
    assert schedule_key("s", 1.0) == schedule_key("s", 1.0)
    assert schedule_key("s", 1.0) != schedule_key("s", 2.0)
