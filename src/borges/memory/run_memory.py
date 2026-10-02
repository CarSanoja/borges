from __future__ import annotations

from borges.analysis.code_guard import check_code
from borges.analysis.models import AnalysisPlan, DatasetProfile, Judgement, Option, Step
from borges.analysis.option_signature import normalise_text
from borges.garden.models import Garden
from borges.memory.kinds import MemoryKind
from borges.memory.recalled import Recalled
from borges.memory.session import MemorySession
from borges.memory.signatures import (
    coding_signature,
    judging_context,
    option_signature,
    option_text,
)

MAX_HINTS = 8
HINT_CHARS = 240


class RunMemory:
    """What the judge, coder, adversary and planner remember, as the pipeline asks for it."""

    def __init__(self, session: MemorySession) -> None:
        self.session = session
        self._code_signatures: dict[tuple[str, str], str] = {}
        self._recalled_code: dict[tuple[str, str], str] = {}
        self.finished = False

    def finish(self) -> None:
        if self.finished:
            return
        self.finished = True
        try:
            self.session.flush()
        finally:
            self.session.repo.close()

    def attach(self, profile: DatasetProfile) -> DatasetProfile:
        self.session.attach(profile)
        notes = {e.payload.get("column"): e for e in self.session.pool(MemoryKind.NOTE)}
        columns = []
        for column in profile.columns:
            entry = notes.get(column.name)
            if entry is not None and entry.text and not column.note:
                self.session.used(MemoryKind.NOTE, Recalled(entry, "exact"))
                column = column.model_copy(update={"note": entry.text})
            columns.append(column)
        return profile.model_copy(update={"columns": columns})

    def recall_verdict(self, plan: AnalysisPlan, step: Step, option: Option) -> Judgement | None:
        context = judging_context(plan, step)
        found = self.session.find(MemoryKind.VERDICT, option_signature(context, option))
        found = found or self.session.similar(MemoryKind.VERDICT, context, option_text(option))
        if found is None:
            return None
        payload = found.payload
        try:
            judgement = Judgement(
                defensibility=float(payload["defensibility"]),
                accepted=bool(payload["accepted"]),
                reason=str(payload["reason"]),
                source=payload.get("source"),
            )
        except (KeyError, TypeError, ValueError):
            return None
        self.session.used(MemoryKind.VERDICT, found)
        return judgement

    def remember_verdict(
        self, plan: AnalysisPlan, step: Step, option: Option, judgement: Judgement
    ) -> None:
        context = judging_context(plan, step)
        self.session.stage(
            MemoryKind.VERDICT,
            option_signature(context, option),
            {
                "ctx": context,
                "step_kind": step.kind,
                "text": option_text(option),
                "defensibility": judgement.defensibility,
                "accepted": judgement.accepted,
                "reason": judgement.reason,
                "source": judgement.source,
            },
        )

    def recall_code(self, plan: AnalysisPlan, step: Step, option: Option) -> str | None:
        signature = coding_signature(plan, step, option)
        self._code_signatures[(step.id, option.id)] = signature
        found = self.session.find(MemoryKind.CODE, signature)
        code = found.payload.get("code") if found else None
        if not isinstance(code, str) or check_code(code, step.kind):
            return None
        assert found is not None
        self.session.used(MemoryKind.CODE, found)
        self._recalled_code[(step.id, option.id)] = code
        return code

    def remember_codes(self, plan: AnalysisPlan, garden: Garden) -> None:
        ran = {
            (step_id, option_id)
            for universe in garden.universes.values()
            if universe.status == "done"
            for step_id, option_id in universe.choices.items()
        }
        for step in plan.steps:
            for option in step.options:
                key = (step.id, option.id)
                signature = self._code_signatures.get(key)
                if signature is None or option.code is None or key not in ran:
                    continue
                if self._recalled_code.get(key) == option.code:
                    continue
                self.session.stage(
                    MemoryKind.CODE,
                    signature,
                    {"code": option.code, "step_kind": step.kind, "text": option_text(option)},
                )

    def blocked(self, plan: AnalysisPlan, step: Step, option: Option) -> Recalled | None:
        context = judging_context(plan, step)
        found = self.session.find(MemoryKind.ADVERSARY, option_signature(context, option))
        found = found or self.session.similar(MemoryKind.ADVERSARY, context, option_text(option))
        if found is None or found.payload.get("why") != "rejected":
            return None
        self.session.used(MemoryKind.ADVERSARY, found)
        return found

    def remember_blocked(
        self, plan: AnalysisPlan, step: Step, option: Option, why: str, reason: str
    ) -> None:
        context = judging_context(plan, step)
        self.session.stage(
            MemoryKind.ADVERSARY,
            option_signature(context, option),
            {
                "ctx": context,
                "question": normalise_text(plan.question),
                "step_kind": step.kind,
                "text": option_text(option),
                "label": option.label,
                "spec": option.spec,
                "why": why,
                "reason": reason,
            },
        )

    def avoid_hints(self, plan: AnalysisPlan) -> list[str]:
        hints: list[str] = []
        question = normalise_text(plan.question)
        entries = sorted(
            self.session.pool(MemoryKind.ADVERSARY), key=lambda e: e.created_at, reverse=True
        )
        for entry in entries:
            payload = entry.payload
            if payload.get("question") != question:
                continue
            if not any(s.kind == payload.get("step_kind") for s in plan.steps):
                continue
            line = f"{payload.get('label')}: {payload.get('spec')} ({payload.get('why')})"
            hints.append(line[:HINT_CHARS])
            self.session.used(MemoryKind.ADVERSARY, Recalled(entry, "exact"))
            if len(hints) >= MAX_HINTS:
                break
        return hints
