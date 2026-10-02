from __future__ import annotations

from borges.analysis.models import AnalysisPlan, Option, Proposal
from borges.analysis.option_signature import same_option
from borges.analysis.prompts.adversary import build_messages
from borges.analysis.schemas import AdversaryOutput
from borges.garden.models import Universe
from borges.llm.client import LLMClient, Role


async def propose_options(
    llm: LLMClient, plan: AnalysisPlan, baseline: Universe, max_proposals: int = 4
) -> list[Proposal]:
    response = await llm.complete(
        Role.ADVERSARY,
        build_messages(plan, baseline, max_proposals),
        key="adversary",
        schema=AdversaryOutput,
        max_tokens=2500,
    )
    out = AdversaryOutput.model_validate(response.parsed)
    seen_ids = {s.id: {o.id for o in s.options} for s in plan.steps}
    known: dict[str, list[Option]] = {s.id: list(s.options) for s in plan.steps}
    proposals: list[Proposal] = []
    for item in out.proposals:
        if len(proposals) >= max_proposals:
            break
        if item.step_id not in seen_ids:
            continue
        option_id = item.id if item.id.startswith("adv_") else f"adv_{item.id}"
        option = Option(
            id=option_id,
            label=item.label,
            rationale=item.rationale,
            spec=item.spec,
            is_default=False,
            origin="adversary",
            source=item.source,
        )
        if option_id in seen_ids[item.step_id]:
            continue
        if any(same_option(option, other) for other in known[item.step_id]):
            continue
        seen_ids[item.step_id].add(option_id)
        known[item.step_id].append(option)
        proposals.append(Proposal(step_id=item.step_id, option=option))
    return proposals
