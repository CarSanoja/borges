from __future__ import annotations

from typing import Any, cast

from borges.runs.emitter import RunEmitter
from borges.runs.events import StepReplannedData
from borges.runs.pipeline_callbacks import replan_callback


class Emitter:
    def __init__(self) -> None:
        self.sent: list[tuple[str, dict[str, Any]]] = []

    async def emit(self, event_type: str, data: dict[str, Any]) -> None:
        self.sent.append((event_type, data))


async def test_replan_callback_emits_the_failed_and_new_option_ids() -> None:
    emitter = Emitter()
    await replan_callback(cast(RunEmitter, emitter))("red_cards_model", ["a", "b", "c"], ["d", "e"])
    assert emitter.sent == [
        (
            "step.replanned",
            {
                "step_id": "red_cards_model",
                "failed_option_ids": ["a", "b", "c"],
                "new_option_ids": ["d", "e"],
            },
        )
    ]
    assert StepReplannedData.model_validate(emitter.sent[0][1]).new_option_ids == ["d", "e"]
