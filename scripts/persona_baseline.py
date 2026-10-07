"""Run the persona-sampling baseline on a case: N independent analysts, one analysis each.

Needs a Nebius key (it calls the planner and coder models). Run from the repository root:
    uv run --no-sync python scripts/persona_baseline.py --case fertility_religiosity --n 12
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from borges.analysis.profile import profile_dataframe  # noqa: E402
from borges.cases.registry import CaseRegistry  # noqa: E402
from borges.config import get_settings  # noqa: E402
from borges.evaluation.persona_baseline import PERSONAS, persona_plan, run_persona  # noqa: E402
from borges.llm.factory import make_llm  # noqa: E402
from borges.runs.inputs import resolve_run  # noqa: E402
from borges.runs.models import RunRequest  # noqa: E402
from borges.runs.pipeline_data import load_dataframe  # noqa: E402
from borges.sandbox.limits import ResourceLimits  # noqa: E402
from borges.sandbox.local_backend import LocalBackend  # noqa: E402


async def analyst(index, llm, backend, profile, resolved, timeout_s, gate) -> dict:
    async with gate:
        started = time.monotonic()
        row = {"index": index, "persona": PERSONAS[index % len(PERSONAS)]}
        try:
            plan = await persona_plan(
                llm, profile, resolved.question, resolved.decision_rule, index
            )
            row |= await run_persona(llm, backend, plan, resolved.data, timeout_s)
        except Exception as exc:
            row |= {"status": "failed", "error": f"{type(exc).__name__}: {exc}"[:400]}
        row["wall_s"] = round(time.monotonic() - started, 1)
        print(json.dumps({k: row.get(k) for k in ("index", "status", "verdict", "p_value")}))
        return row


async def main(case_id: str, n: int, cap: float, scratch: Path) -> dict:
    settings = get_settings()
    registry = CaseRegistry(settings.borges_cases_dir)
    resolved = resolve_run(RunRequest(case_id=case_id, llm="nebius"), registry, settings)
    profile = profile_dataframe(
        load_dataframe(resolved.data), resolved.dataset_name, column_notes=resolved.column_notes
    )
    llm = make_llm(settings, mode="nebius", run_cap_usd=cap)
    backend = LocalBackend(scratch / case_id, ephemeral=True, limits=ResourceLimits())
    gate = asyncio.Semaphore(3)
    try:
        rows = await asyncio.gather(
            *(
                analyst(i, llm, backend, profile, resolved, settings.borges_step_timeout_s, gate)
                for i in range(n)
            )
        )
    finally:
        await backend.close()
    return {"case": case_id, "n": n, "totals": llm.totals.model_dump(), "analysts": rows}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--case", required=True)
    parser.add_argument("--n", type=int, default=12)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--cap", type=float, default=0.5)
    parser.add_argument("--scratch", type=Path, default=Path("/tmp/borges_persona_scratch"))
    args = parser.parse_args()
    payload = asyncio.run(main(args.case, args.n, args.cap, args.scratch))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, indent=1))
    print(json.dumps(payload["totals"]))
