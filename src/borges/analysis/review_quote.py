"""A review that calls an option unfaithful must quote words of that option's own spec.

A hurricanes square-root option at d988b34 wrote its result into log_alldeaths_plus1, the name
every option of the step writes. The reviewer said its spec asked for np.log1p, which the spec
does not contain; the repair rewrote the code as log1p and the re-review rejected it, so the
square-root and inverse-normal options were lost. A quote the spec does not contain is put back to
the reviewer once; if it still does not match, the review point is dropped.
"""

from __future__ import annotations

import re

from borges.analysis.schemas import ReviewerOutput, ReviewVerdict
from borges.llm.client import LLMClient, LLMError, Role

QUOTE_CHARS = re.compile(r"[`'\"‘’“”]")
ASK = (
    "These quotes are not in the spec of the option they are about: {listed}. Review those "
    "options again against their own spec. When the code contradicts it, copy the contradicted "
    "words of that spec exactly into quote; otherwise answer faithful=true."
)
UNQUOTED = (
    "review point dropped: it quoted {quote!r} as the option's spec, and the spec does not "
    "contain those words"
)


def plain(text: str) -> str:
    return " ".join(QUOTE_CHARS.sub("", text).lower().split()).strip(" .;:,")


def unsupported(verdict: ReviewVerdict, spec: str) -> bool:
    quote = plain(verdict.quote)
    return not verdict.faithful and bool(quote) and quote not in plain(spec)


async def checked_quotes(
    llm: LLMClient,
    messages: list[dict[str, str]],
    out: ReviewerOutput,
    specs: dict[str, str],
    key: str,
) -> list[ReviewVerdict]:
    missing = {v.option_id for v in out.verdicts if unsupported(v, specs.get(v.option_id, ""))}
    if not missing:
        return out.verdicts
    listed = "; ".join(
        f"{v.option_id}: {v.quote!r}" for v in out.verdicts if v.option_id in missing
    )
    follow = [
        *messages,
        {"role": "assistant", "content": out.model_dump_json()},
        {"role": "user", "content": ASK.format(listed=listed)},
    ]
    try:
        response = await llm.complete(
            Role.REVIEWER, follow, key=f"{key}:quote", schema=ReviewerOutput, max_tokens=1500
        )
        again = {v.option_id: v for v in ReviewerOutput.model_validate(response.parsed).verdicts}
    except LLMError:
        again = {}
    checked = []
    for verdict in out.verdicts:
        if verdict.option_id in missing:
            verdict = again.get(verdict.option_id, verdict)
        if unsupported(verdict, specs.get(verdict.option_id, "")):
            verdict = verdict.model_copy(
                update={"faithful": True, "problem": UNQUOTED.format(quote=verdict.quote)}
            )
        checked.append(verdict)
    return checked
