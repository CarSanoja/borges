from __future__ import annotations

from borges.analysis.ids import slug_id
from borges.analysis.models import AnalysisPlan, Option, Proposal
from borges.analysis.option_signature import same_option
from borges.analysis.prompts.adversary import build_messages
from borges.analysis.schemas import AdversaryOutput
from borges.analysis.shadow_columns import shadow_copies
from borges.garden.models import Universe
from borges.llm.client import LLMClient, Role

REPEATS = (
    "Every proposal repeats an option the plan already has: {labels}. A new label for an "
    "existing spec is the same option, and repeats are discarded. Return at least one option "
    "whose implementation differs from every option of its step: another threshold or exclusion "
    "rule, another model family or covariance estimator, another covariate set or another "
    "construction of a derived variable, at a step where the baseline traces show the data "
    "respond. Keep it defensible; the judge rejects what is not."
)
SHADOWS = (
    "These proposals write a changed copy of a dataset column under a new name: {labels}. The "
    "steps after them read the column's own name, so they would have no effect and are "
    "discarded. Propose them again so that they change the column itself, in place (for "
    "example clip 'campaign' at 10 and keep the name 'campaign')."
)


async def _ask(llm: LLMClient, messages: list[dict[str, str]], key: str) -> AdversaryOutput:
    response = await llm.complete(
        Role.ADVERSARY, messages, key=key, schema=AdversaryOutput, max_tokens=2500
    )
    return AdversaryOutput.model_validate(response.parsed)


def _collect(
    plan: AnalysisPlan, out: AdversaryOutput, max_proposals: int, taken: list[Proposal]
) -> tuple[list[Proposal], list[str], list[str]]:
    seen_ids = {s.id: {o.id for o in s.options} for s in plan.steps}
    known: dict[str, list[Option]] = {s.id: list(s.options) for s in plan.steps}
    for earlier in taken:
        seen_ids[earlier.step_id].add(earlier.option.id)
        known[earlier.step_id].append(earlier.option)
    columns = {c.name for c in plan.dataset.columns}
    produces = {s.id: s.produces for s in plan.steps}
    proposals: list[Proposal] = []
    repeats: list[str] = []
    shadows: list[str] = []
    for item in out.proposals:
        if len(proposals) >= max_proposals:
            break
        if item.step_id not in seen_ids:
            continue
        if shadow_copies(item.spec, produces[item.step_id], columns):
            shadows.append(item.label)
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
    return proposals, repeats, shadows


async def propose_options(
    llm: LLMClient,
    plan: AnalysisPlan,
    baseline: Universe,
    max_proposals: int = 4,
    avoid: list[str] | None = None,
) -> list[Proposal]:
    """Ask once more when every proposal repeats an option the plan already has, or when a
    proposal writes a changed copy of a column that no later step reads."""
    messages = build_messages(plan, baseline, max_proposals, avoid)
    out = await _ask(llm, messages, "adversary")
    proposals, repeats, shadows = _collect(plan, out, max_proposals, [])
    notes = [REPEATS.format(labels=_quoted(repeats))] if repeats and not proposals else []
    if shadows:
        notes.append(SHADOWS.format(labels=_quoted(shadows)))
    if not notes or len(proposals) >= max_proposals:
        return proposals
    retry = [
        *messages,
        {"role": "assistant", "content": out.model_dump_json()},
        {"role": "user", "content": " ".join(notes)},
    ]
    out = await _ask(llm, retry, "adversary:retry")
    more = _collect(plan, out, max_proposals - len(proposals), proposals)[0]
    return [*proposals, *more]


def _quoted(labels: list[str]) -> str:
    return ", ".join(f"'{label}'" for label in labels)
