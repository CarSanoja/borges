"""One structured call per role against Nemotron 3 Nano on Ollama (local, not Token Factory)."""

from __future__ import annotations

import argparse
import asyncio
import sys
import time

from pydantic import BaseModel

from borges.analysis.schemas import (
    AdversaryOutput,
    CoderOutput,
    JudgeOutput,
    NarratorOutput,
    PlannerOutput,
)
from borges.config import Settings
from borges.llm.client import Role
from borges.llm.factory import make_llm
from borges.llm.local_models import LOCAL_LABEL, THINKING_ROLES, local_role_models

CALLS: dict[Role, tuple[str, type[BaseModel], int]] = {
    Role.PLANNER: (
        "Plan a two-step analysis (cleaning, test) of whether a checkout redesign raised "
        "conversion. Step kinds are free text; give each step two options.",
        PlannerOutput,
        4096,
    ),
    Role.CODER: (
        "Write a Python function clean(df) that drops rows with a missing 'revenue' column "
        "and returns the DataFrame. Put the code in the 'code' field.",
        CoderOutput,
        1500,
    ),
    Role.ADVERSARY: (
        "Propose one defensible alternative way to handle outliers in revenue, for step id "
        "'outliers'. Give it id 'trim1', a label, a rationale and a spec.",
        AdversaryOutput,
        2500,
    ),
    Role.JUDGE: (
        "Judge whether trimming the top 1 percent of revenue is a defensible analyst choice "
        "when revenue is heavy tailed.",
        JudgeOutput,
        800,
    ),
    Role.NARRATOR: (
        "In two sentences, tell the story of a result that flipped from SHIP to HOLD when the "
        "top 1 percent of revenue was trimmed, and list one caveat.",
        NarratorOutput,
        1200,
    ),
}


async def smoke(thinking: frozenset[Role]) -> int:
    settings = Settings()
    llm = make_llm(settings, mode="local")
    llm.cache = None
    llm.role_models = local_role_models(settings.borges_local_model, thinking)
    print(f"{LOCAL_LABEL}: {settings.borges_local_model} at {settings.borges_local_base_url}")
    failures = 0
    for role, (prompt, schema, max_tokens) in CALLS.items():
        started = time.perf_counter()
        before = (llm.totals.tokens_in, llm.totals.tokens_out)
        try:
            response = await llm.complete(
                role,
                [{"role": "user", "content": prompt}],
                key=f"smoke:{role.value}",
                schema=schema,
                max_tokens=max_tokens,
            )
            status = "ok" if response.parsed is not None else "no-json"
        except Exception as exc:
            status = f"FAILED {type(exc).__name__}: {exc}"
            failures += 1
        tokens_in = llm.totals.tokens_in - before[0]
        tokens_out = llm.totals.tokens_out - before[1]
        think = "think" if role in thinking else "no-think"
        print(
            f"{role.value:9} {think:8} {time.perf_counter() - started:6.1f}s "
            f"{tokens_in:5} in {tokens_out:5} out  {status}"
        )
    return 1 if failures else 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--think", default=",".join(r.value for r in THINKING_ROLES))
    args = parser.parse_args()
    roles = frozenset(Role(name) for name in args.think.split(",") if name)
    return asyncio.run(smoke(roles))


if __name__ == "__main__":
    sys.exit(main())
