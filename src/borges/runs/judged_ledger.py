from __future__ import annotations

from dataclasses import dataclass, field

from borges.analysis.models import AnalysisPlan, Judgement, Option
from borges.analysis.option_signature import same_option


@dataclass(frozen=True)
class JudgedEntry:
    option: Option
    judgement: Judgement


@dataclass
class JudgedLedger:
    entries: dict[str, list[JudgedEntry]] = field(default_factory=dict)

    def record(self, step_id: str, option: Option, judgement: Judgement) -> None:
        self.entries.setdefault(step_id, []).append(JudgedEntry(option, judgement))

    def find(self, step_id: str, option: Option) -> JudgedEntry | None:
        return next(
            (e for e in self.entries.get(step_id, []) if same_option(e.option, option)), None
        )


def duplicate_in_plan(plan: AnalysisPlan, step_id: str, option: Option) -> Option | None:
    step = plan.step(step_id)
    return next((o for o in step.options if same_option(o, option)), None)
