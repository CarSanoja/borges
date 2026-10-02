from __future__ import annotations

from borges.runs.events import OptionJudgedData


def test_old_judged_events_default_to_the_adversary_origin() -> None:
    data = OptionJudgedData.model_validate(
        {"step_id": "s", "option_id": "o", "defensibility": 0.7, "accepted": True, "reason": "r"}
    )
    assert data.origin == "adversary"
