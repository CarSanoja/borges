"""Run the full fixed grid of each curated case and compare it with the committed Borges search."""

from __future__ import annotations

import argparse
import asyncio
import json
import platform
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from borges.evaluation.grid_borges import compare, recording_summary  # noqa: E402
from borges.evaluation.grid_plan import (  # noqa: E402
    enumerate_grid,
    grid_size,
    load_events,
    sample_grid,
    seeded_plan,
)
from borges.evaluation.grid_report import render_markdown  # noqa: E402
from borges.evaluation.grid_run import run_grid  # noqa: E402
from borges.evaluation.grid_stats import grid_summary  # noqa: E402
from borges.sandbox.limits import ResourceLimits  # noqa: E402
from borges.sandbox.local_backend import LocalBackend  # noqa: E402

CASES = ("red_cards", "checkout_ab", "marp_norms", "marp_religiosity")
DEFAULT_OUT = ROOT / "evidence" / "grid_vs_search.json"
DEFAULT_MD = ROOT / "evidence" / "grid_vs_search.md"
DEFAULT_SCRATCH = Path("/tmp/borges_grid_scratch")


def progress_printer(case_id: str, started: float):
    def show(done: int, total: int) -> None:
        print(
            f"[{case_id}] {done}/{total} universes, {time.monotonic() - started:.0f}s", flush=True
        )

    return show


async def run_case(
    case_id: str, cap: int | None, seed: int, concurrency: int, scratch: Path
) -> dict:
    directory = ROOT / "cases" / case_id
    spec = json.loads((directory / "case.json").read_text(encoding="utf-8"))
    events = load_events(directory / "recorded" / "events.jsonl")
    plan = seeded_plan(events)
    data = (directory / spec["dataset_file"]).read_bytes()
    everything = enumerate_grid(plan)
    chosen = sample_grid(everything, plan, cap, seed)
    backend = LocalBackend(scratch / case_id, ephemeral=True, limits=ResourceLimits())
    started = time.monotonic()
    try:
        run = await run_grid(
            backend,
            plan,
            data,
            chosen,
            concurrency=concurrency,
            progress=progress_printer(case_id, started),
        )
    finally:
        await backend.close()
    grid = grid_summary(plan, run.garden, run.wall_s, grid_size(plan), cap, seed, run.checkpoints)
    borges = recording_summary(events, plan)
    return {
        "case": case_id,
        "question": spec["question"],
        "decision_rule": spec["decision_rule"],
        "options_per_step": {s.id: len(s.options) for s in plan.steps},
        "grid": grid,
        "borges": borges,
        "comparison": compare(grid, borges),
    }


def write_outputs(out: Path, md: Path, results: dict, meta: dict) -> None:
    document = {"meta": meta, "cases": results}
    out.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")
    md.write_text(render_markdown(document), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases", nargs="+", default=list(CASES), choices=CASES)
    parser.add_argument("--cap", type=int, default=None)
    parser.add_argument("--caps", nargs="*", default=[], help="per case: case=cap")
    parser.add_argument("--seed", type=int, default=20261002)
    parser.add_argument("--concurrency", type=int, default=6)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--md", type=Path, default=DEFAULT_MD)
    parser.add_argument("--scratch", type=Path, default=DEFAULT_SCRATCH)
    parser.add_argument("--render-only", action="store_true")
    args = parser.parse_args()
    caps = {item.split("=")[0]: int(item.split("=")[1]) for item in args.caps}
    existing: dict = {}
    if args.out.is_file():
        existing = json.loads(args.out.read_text(encoding="utf-8"))
    results = dict(existing.get("cases", {}))
    meta = dict(existing.get("meta", {}))
    if args.render_only:
        args.md.write_text(render_markdown({"meta": meta, "cases": results}), encoding="utf-8")
        return
    meta.update(
        {
            "machine": f"{platform.machine()} {platform.system()} {platform.release()}",
            "python": platform.python_version(),
            "backend": "local sandbox (LocalBackend), shared prefixes via GardenExecutor",
            "concurrency": args.concurrency,
        }
    )
    for case_id in args.cases:
        cap = caps.get(case_id, args.cap)
        results[case_id] = asyncio.run(
            run_case(case_id, cap, args.seed, args.concurrency, args.scratch)
        )
        write_outputs(args.out, args.md, results, meta)
        print(f"[{case_id}] written", flush=True)


if __name__ == "__main__":
    main()
