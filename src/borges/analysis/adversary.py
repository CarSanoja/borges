from __future__ import annotations

from borges.analysis.ids import slug_id
from borges.analysis.models import AnalysisPlan, Option, Proposal
from borges.analysis.option_signature import same_option
from borges.analysis.prompts.adversary import build_messages
from borges.analysis.schemas import AdversaryOutput
from borges.garden.models import Universe
from borges.llm.client import LLMClient, Role

REPEATS = (
    "Every proposal repeats an option the plan already has: {labels}. A new label for an "
    "existing spec is the same option. Propose options whose implementation differs from every "
    "option of their step."
)


async def _ask(llm: LLMClient, messages: list[dict[str, str]], key: str) -> AdversaryOutput:
    response = await llm.complete(
        Role.ADVERSARY, messages, key=key, schema=AdversaryOutput, max_tokens=2500
    )
    return AdversaryOutput.model_validate(response.parsed)


def _collect(
    plan: AnalysisPlan, out: AdversaryOutput, max_proposals: int
) -> tuple[list[Proposal], list[str]]:
    seen_ids = {s.id: {o.id for o in s.options} for s in plan.steps}
    known: dict[str, list[Option]] = {s.id: list(s.options) for s in plan.steps}
    proposals: list[Proposal] = []
    repeats: list[str] = []
    for item in out.proposals:
        if len(proposals) >= max_proposals:
            break
        if item.step_id not in seen_ids:
            continue
        slug = slug_id(item.id) or "option"
        option_id = slug if slug.startswith("adv_") else f"adv_{slug}"
        option = Option(
            id=option_id,
            label=item.label,
            rationale=item.rationale,
            spec=item.spec,
            is_default=False,
            origin="adversary",
            source=item.source,
        )
        if option_id in seen_ids[item.step_id] or any(
            same_option(option, other) for other in known[item.step_id]
        ):
            repeats.append(item.label)
            continue
        seen_ids[item.step_id].add(option_id)
        known[item.step_id].append(option)
        proposals.append(Proposal(step_id=item.step_id, option=option))
    return proposals, repeats


async def propose_options(
    llm: LLMClient,
    plan: AnalysisPlan,
    baseline: Universe,
    max_proposals: int = 4,
    avoid: list[str] | None = None,
) -> list[Proposal]:
    """Ask once more when every proposal repeats an option the plan already has."""
    messages = build_messages(plan, baseline, max_proposals, avoid)
    out = await _ask(llm, messages, "adversary")
    proposals, repeats = _collect(plan, out, max_proposals)
    if proposals or not repeats:
        return proposals
    labels = ", ".join(f"'{label}'" for label in repeats)
    retry = [
        *messages,
        {"role": "assistant", "content": out.model_dump_json()},
        {"role": "user", "content": REPEATS.format(labels=labels)},
    ]
    return _collect(plan, await _ask(llm, retry, "adversary:retry"), max_proposals)[0]
