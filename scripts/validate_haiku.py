"""Run Borges's actual analysis pipeline with Haiku, leaving production routing unchanged."""

from __future__ import annotations

import argparse
import asyncio
import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path

from dotenv import dotenv_values
from haiku_validation_client import HAIKU, HaikuValidationLLM
from haiku_validation_identity import validation_gateway

from borges.armor.llm_armor import LLMArmor
from borges.armor.report import ArmorReport
from borges.cases.registry import CaseRegistry
from borges.config import REPO_ROOT, Settings
from borges.gateway.dataset_columns import columns_of
from borges.runs.bus import EventBus
from borges.runs.emitter import RunEmitter
from borges.runs.inputs import resolve_run
from borges.runs.models import RunRequest
from borges.runs.orchestrator import new_run_id
from borges.runs.pipeline import Pipeline
from borges.runs.store import RunStore
from borges.sandbox.factory import make_backend
from borges.telemetry.instrumented_backend import instrument_backend
from borges.telemetry.instrumented_llm import instrument_llm


def validation_settings(home: Path, cap: float) -> Settings:
    policy = json.loads((REPO_ROOT / "policy/gateway.json").read_text())
    policy["description"] = "Temporary Haiku validation; production policy remains unchanged."
    policy["run"]["max_cost_usd"] = cap
    policy["retry"]["max_attempts"] = 1
    for agent in policy["agents"].values():
        agent["models"] = [HAIKU.id]
        agent["alternatives"] = []
        agent["max_cost_usd_per_run"] = min(agent["max_cost_usd_per_run"], cap)
    path = home / "gateway.json"
    home.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(policy, indent=2) + "\n")
    return Settings(
        _env_file=None,
        borges_home=home,
        borges_runs_dir=home / "runs",
        borges_gateway_policy=path,
        borges_concurrency=2,
        borges_registry_enforce=False,
        borges_memory=False,
    )


async def run_case(args, case_id: str, key: str) -> dict:
    settings = validation_settings(args.home, args.run_cap_usd)
    raw = HaikuValidationLLM(key, args.home, args.run_cap_usd, args.total_cap_usd)
    registry = CaseRegistry(settings.borges_cases_dir)
    request = RunRequest(case_id=case_id, llm="nebius", max_universes=40)
    resolved = resolve_run(request, registry, settings)
    run_id = new_run_id()
    store = RunStore(settings.borges_runs_dir)
    store.create(run_id, {"llm": "anthropic", "model": HAIKU.id, "case_id": case_id})
    bus = EventBus(store)
    bus.open(run_id)
    emitter = RunEmitter(run_id, store, bus)
    armor = ArmorReport()
    gateway, identity = validation_gateway(
        settings, run_id, HAIKU.id, LLMArmor(armor), columns_of(resolved.data)
    )
    llm = instrument_llm(raw, identity, gateway)
    backend = instrument_backend(make_backend(settings, "local"), gateway)
    pipeline = Pipeline(settings, llm, backend, emitter, resolved, armor)
    result = {"case": case_id, "run_id": run_id, "provider": "anthropic", "model": HAIKU.id}
    try:
        with gateway.bind():
            report = await pipeline.run()
        if not report.narrative.strip() or any(
            caveat.startswith("Narrative unavailable:") for caveat in report.caveats
        ):
            raise ValueError("the final narrative did not complete")
        result.update(status="pass", report=report.model_dump(mode="json"))
        (settings.borges_runs_dir / run_id / "plan.json").write_text(
            pipeline.planned.model_dump_json(indent=2)
        )
    except Exception as exc:
        result.update(status="fail", error=f"{type(exc).__name__}: {exc}")
    finally:
        result["usage"] = raw.totals.model_dump(mode="json")
        gateway.budgets.release_outstanding()
        await backend.close()
        await raw.client.aclose()
        bus.close(run_id)
    return result


async def validate(args) -> int:
    key = dotenv_values(args.env_file).get("ANTHROPIC_API_KEY")
    if not key:
        raise SystemExit("ANTHROPIC_API_KEY is missing from the private --env-file")
    commit = await asyncio.to_thread(
        subprocess.check_output, ["git", "rev-parse", "HEAD"], text=True
    )
    commit = commit.strip()
    results = []
    for case_id in args.cases.split(","):
        print(
            f"Validating {case_id} with {HAIKU.id}; per-run cap ${args.run_cap_usd:.2f}", flush=True
        )
        result = await run_case(args, case_id, key)
        results.append(result)
        evidence = {
            "checked_at": datetime.now(UTC).isoformat(),
            "source_commit": commit,
            "purpose": "Live Haiku engine validation, separate from historical Nemotron recordings",
            "total_cap_usd": args.total_cap_usd,
            "results": results,
        }
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(evidence, indent=2) + "\n")
        print(json.dumps({k: result[k] for k in ("case", "status", "usage")}), flush=True)
        if result["status"] != "pass":
            print(result["error"], flush=True)
            return 1
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env-file", type=Path, default=REPO_ROOT / ".env.haiku")
    parser.add_argument("--cases", default="checkout_ab,red_cards")
    parser.add_argument("--home", type=Path, default=REPO_ROOT / ".borges/haiku-validation")
    parser.add_argument("--run-cap-usd", type=float, default=0.25)
    parser.add_argument("--total-cap-usd", type=float, default=0.50)
    parser.add_argument(
        "--out", type=Path, default=REPO_ROOT / "evidence/test-suite/haiku-2026-10-25.json"
    )
    args = parser.parse_args()
    if not 0 < args.run_cap_usd <= args.total_cap_usd <= 0.50:
        parser.error("validation caps must satisfy 0 < run cap <= total cap <= $0.50")
    return asyncio.run(validate(args))


if __name__ == "__main__":
    raise SystemExit(main())
