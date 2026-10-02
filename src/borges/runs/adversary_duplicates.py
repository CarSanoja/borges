from __future__ import annotations

from borges.analysis.models import AnalysisPlan, Proposal
from borges.memory.run_memory import RunMemory
from borges.runs.emitter import RunEmitter
from borges.runs.events import OptionJudgedData
from borges.runs.judged_ledger import JudgedLedger, duplicate_in_plan


async def _emit_rejected(
    emitter: RunEmitter, step_id: str, option_id: str, remembered: dict
) -> None:
    data = OptionJudgedData(
        step_id=step_id,
        option_id=option_id,
        defensibility=0.0,
        accepted=False,
        reason=f"rejected in an earlier run: {remembered.get('reason', '')}",
        origin="adversary",
    )
    await emitter.emit("option.judged", data.model_dump(mode="json"))


async def drop_duplicates(
    plan: AnalysisPlan,
    emitter: RunEmitter,
    ledger: JudgedLedger | None,
    proposals: list[Proposal],
    memory: RunMemory | None = None,
) -> list[Proposal]:
    fresh: list[Proposal] = []
    for proposal in proposals:
        step_id, option = proposal.step_id, proposal.option
        entry = ledger.find(step_id, option) if ledger is not None else None
        if entry is None and memory is not None:
            remembered = memory.blocked(plan, plan.step(step_id), option)
            if remembered is not None:
                await _emit_rejected(emitter, step_id, option.id, remembered.payload)
                continue
        if entry is not None and not entry.judgement.accepted:
            data = OptionJudgedData(
                step_id=step_id,
                option_id=option.id,
                defensibility=entry.judgement.defensibility,
                accepted=False,
                reason=(
                    f"same as planner alternative {entry.option.id}, already judged: "
                    f"{entry.judgement.reason}"
                ),
                origin="adversary",
            )
            await emitter.emit("option.judged", data.model_dump(mode="json"))
            continue
        if entry is not None or duplicate_in_plan(plan, step_id, option) is not None:
            if memory is not None and entry is None:
                memory.remember_blocked(
                    plan, plan.step(step_id), option, "duplicate", "repeats an option of the plan"
                )
            continue
        fresh.append(proposal)
    return fresh
