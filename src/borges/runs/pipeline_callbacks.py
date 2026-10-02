from __future__ import annotations

from collections.abc import Awaitable, Callable

from borges.runs.emitter import RunEmitter
from borges.runs.events import OptionCodedData, OptionReviewedData, OptionSmokeData

OnCoded = Callable[[str, str, bool, int, str | None, list[str] | None], Awaitable[None]]
OnSmoke = Callable[..., Awaitable[None]]
OnReview = Callable[[str, str, bool, bool, str, str], Awaitable[None]]


def coding_callbacks(emitter: RunEmitter) -> tuple[OnCoded, OnSmoke, OnReview]:
    async def on_coded(
        step_id: str,
        option_id: str,
        ok: bool,
        attempts: int,
        error: str | None,
        models: list[str] | None = None,
    ) -> None:
        payload = OptionCodedData(
            step_id=step_id,
            option_id=option_id,
            ok=ok,
            attempts=attempts,
            error=error,
            models=models or [],
        )
        await emitter.emit("option.coded", payload.model_dump(mode="json"))

    async def on_smoke(
        step_id: str,
        option_id: str,
        status: str,
        attempts: int,
        error: str | None,
        models: list[str] | None = None,
        sample_rows: int | None = None,
    ) -> None:
        payload = OptionSmokeData(
            step_id=step_id,
            option_id=option_id,
            status=status,
            attempts=attempts,
            error=error,
            models=models or [],
            sample_rows=sample_rows,
        )
        data = payload.model_dump(mode="json")
        if sample_rows is None:
            data.pop("sample_rows")
        await emitter.emit("option.smoke", data)

    async def on_review(
        step_id: str,
        option_id: str,
        faithful: bool,
        changes_estimand: bool,
        problem: str,
        model: str,
    ) -> None:
        payload = OptionReviewedData(
            step_id=step_id,
            option_id=option_id,
            faithful=faithful,
            changes_estimand=changes_estimand,
            problem=problem,
            model=model,
        )
        await emitter.emit("option.reviewed", payload.model_dump(mode="json"))

    return on_coded, on_smoke, on_review
