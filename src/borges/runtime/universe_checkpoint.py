from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from borges.analysis.models import AnalysisPlan, Option
from borges.garden.models import Universe

UNIVERSE_PREFIX = "universe:"


def universe_key(universe_id: str) -> str:
    return f"{UNIVERSE_PREFIX}{universe_id}"


def universe_payload(universe: Universe, plan: AnalysisPlan, root_id: str | None) -> dict[str, Any]:
    options = {
        step.id: step.option(universe.choices[step.id]).model_dump(mode="json")
        for step in plan.steps
        if step.id in universe.choices
    }
    return {
        "universe": universe.model_dump(mode="json"),
        "options": options,
        "root_id": root_id,
    }


@dataclass
class RestoredUniverses:
    payloads: dict[str, dict[str, Any]] = field(default_factory=dict)
    order: list[str] = field(default_factory=list)

    def __bool__(self) -> bool:
        return bool(self.payloads)

    @property
    def ids(self) -> set[str]:
        return set(self.payloads)

    def universe(self, universe_id: str) -> Universe:
        return Universe.model_validate(self.payloads[universe_id]["universe"])

    def baseline(self) -> dict[str, Any] | None:
        for universe_id in self.order:
            payload = self.payloads[universe_id]
            if payload["universe"]["kind"] == "baseline":
                return payload
        return None

    def checkpoint_ids(self) -> set[str]:
        ids: set[str] = set()
        for payload in self.payloads.values():
            ids.update(payload["universe"]["checkpoints"])
            if payload.get("root_id"):
                ids.add(payload["root_id"])
        return ids


def apply_options(plan: AnalysisPlan, payload: dict[str, Any]) -> None:
    for step_id, raw in payload.get("options", {}).items():
        restored = Option.model_validate(raw)
        step = next((s for s in plan.steps if s.id == step_id), None)
        if step is None:
            continue
        for index, existing in enumerate(step.options):
            if existing.id == restored.id and existing.code != restored.code:
                step.options[index] = restored


def load_restored(rows: list[tuple[str, int, dict[str, Any]]]) -> RestoredUniverses:
    restored = RestoredUniverses()
    for key, _seq, payload in rows:
        universe_id = key.removeprefix(UNIVERSE_PREFIX)
        restored.payloads[universe_id] = payload
        restored.order.append(universe_id)
    if restored.baseline() is None:
        return RestoredUniverses()
    return restored
