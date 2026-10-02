from __future__ import annotations

from borges.telemetry.caller import calling_as, current_caller


def test_default_caller_is_anonymous() -> None:
    assert current_caller().principal is None


def test_calling_as_nests_and_restores() -> None:
    with calling_as(principal="svc:planner", agent="planner"):
        with calling_as(step_id="s1", option_id="a"):
            caller = current_caller()
            assert (caller.principal, caller.step_id, caller.option_id) == (
                "svc:planner",
                "s1",
                "a",
            )
        assert current_caller().step_id is None
        assert current_caller().principal == "svc:planner"
    assert current_caller().principal is None
