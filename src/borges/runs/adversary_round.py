from __future__ import annotations

from borges.analysis.adversary import propose_options
from borges.analysis.coder import _smoke_repair, code_option
from borges.analysis.judge import judge_option
from borges.analysis.models import AnalysisPlan, Option, Proposal, Step
from borges.analysis.smoke_extra import smoke_extra_option
from borges.analysis.smoke_types import SmokeConfig
from borges.garden.models import Universe
from borges.llm.client import BudgetExceeded, LLMClient, LLMError
from borges.llm.gather import gather_cancelling
from borges.runs.adversary_review import review_proposal
from borges.runs.emitter import RunEmitter
from borges.runs.events import OptionCodedData, OptionJudgedData
from borges.runs.runner import UniverseRunner, publish_plan


async def _smoke(
    llm: LLMClient,
    plan: AnalysisPlan,
    emitter: RunEmitter,
    smoke: SmokeConfig,
    step: Step,
    option: Option,
) -> tuple[bool, Option | None]:
    async def repair(
        target: Step, candidate: Option, error: str, attempt: int
    ) -> tuple[str, str | None, str]:
        return await _smoke_repair(llm, plan, target, candidate, error, attempt)

    outcome = await smoke_extra_option(smoke, repair, step, option)
    if outcome is None:
        return False, option
    if outcome.status != "failed":
        return True, outcome.option
    failed = OptionCodedData(
        step_id=step.id,
        option_id=option.id,
        ok=False,
        attempts=outcome.attempts,
        error=outcome.error,
        models=outcome.models,
    )
    await emitter.emit("option.coded", failed.model_dump(mode="json"))
    return True, None


async def _judge_and_code(
    llm: LLMClient,
    plan: AnalysisPlan,
    emitter: RunEmitter,
    proposal: Proposal,
    smoke: SmokeConfig | None = None,
) -> tuple[str, Option] | None:
    step = plan.step(proposal.step_id)
    option = proposal.option
    try:
        judgement = await judge_option(llm, plan, step, option)
    except LLMError as exc:
        rejected = OptionJudgedData(
            step_id=step.id,
            option_id=option.id,
            defensibility=0.0,
            accepted=False,
            reason=f"judge failed: {exc}",
            origin="adversary",
        )
        await emitter.emit("option.judged", rejected.model_dump(mode="json"))
        return None
    judged = OptionJudgedData(
        step_id=step.id,
        option_id=option.id,
        defensibility=judgement.defensibility,
        accepted=judgement.accepted,
        reason=judgement.reason,
        origin="adversary",
    )
    await emitter.emit("option.judged", judged.model_dump(mode="json"))
    if not judgement.accepted:
        return None
    option = option.model_copy(
        update={
            "defensibility": judgement.defensibility,
            "source": judgement.source or option.source,
        }
    )
    try:
        code = await code_option(llm, plan, step, option)
    except BudgetExceeded:
        raise
    except Exception as exc:
        failed = OptionCodedData(
            step_id=step.id, option_id=option.id, ok=False, attempts=1, error=str(exc)
        )
        await emitter.emit("option.coded", failed.model_dump(mode="json"))
        return None
    option = option.model_copy(update={"code": code})
    if smoke is not None:
        smoked, option_after = await _smoke(llm, plan, emitter, smoke, step, option)
        if smoked:
            return None if option_after is None else (step.id, option_after)
    reviewed = await review_proposal(llm, plan, emitter, step, option)
    if reviewed is None:
        return None
    return step.id, reviewed


async def run_adversary_round(
    llm: LLMClient,
    plan: AnalysisPlan,
    runner: UniverseRunner,
    emitter: RunEmitter,
    baseline: Universe,
    smoke: SmokeConfig | None = None,
) -> list[Universe]:
    """Propose options from the real baseline state, judge them, then flip each accepted one."""
    try:
        proposed = await propose_options(llm, plan, baseline)
    except LLMError:
        return []
    proposals = [p for p in proposed if any(s.id == p.step_id for s in plan.steps)]
    for proposal in proposals:
        payload = {"step_id": proposal.step_id, "option": proposal.option.model_dump(mode="json")}
        await emitter.emit("option.proposed", payload)
    outcomes = await gather_cancelling(
        _judge_and_code(llm, plan, emitter, p, smoke) for p in proposals
    )
    accepted = [o for o in outcomes if o is not None]
    for step_id, option in accepted:
        plan.step(step_id).options.append(option)
    if proposals:
        await publish_plan(emitter, plan)
    if not accepted:
        return []
    defaults = plan.default_choices()
    choices = [{**defaults, step_id: option.id} for step_id, option in accepted]
    return await runner.run_many(choices, "adversary")
