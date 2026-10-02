from __future__ import annotations

import json
import platform
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

from borges.evaluation.calibration_grid import BASE_SEED, EFFECTS, Cell, Job, build_jobs
from borges.evaluation.calibration_run import run_one
from borges.evaluation.calibration_stats import summarise


def _work(job: Job) -> dict:
    outcome = run_one(job.seed, job.cell.true_effect, job.cell.artefact, n_users=job.cell.n_users)
    return {"cell": job.cell.key, **outcome.to_dict()}


def _done(rows_path: Path) -> list[dict]:
    if not rows_path.exists():
        return []
    return [json.loads(line) for line in rows_path.read_text().splitlines() if line.strip()]


def run_study(
    cells: list[Cell], rows_path: Path, workers: int = 1
) -> tuple[list[dict], dict[str, int]]:
    jobs, scanned = build_jobs(cells)
    rows = _done(rows_path)
    finished = {(r["cell"], r["seed"]) for r in rows}
    pending = [j for j in jobs if (j.cell.key, j.seed) not in finished]
    rows_path.parent.mkdir(parents=True, exist_ok=True)
    with rows_path.open("a") as sink:
        if workers <= 1:
            for job in pending:
                row = _work(job)
                sink.write(json.dumps(row) + "\n")
                sink.flush()
                rows.append(row)
        else:
            with ProcessPoolExecutor(max_workers=workers) as pool:
                futures = [pool.submit(_work, job) for job in pending]
                for future in as_completed(futures):
                    row = future.result()
                    sink.write(json.dumps(row) + "\n")
                    sink.flush()
                    rows.append(row)
    return rows, scanned


def result_document(rows: list[dict], scanned: dict[str, int], cells: list[Cell]) -> dict:
    return {
        "base_seed": BASE_SEED,
        "effects_probability_units": EFFECTS,
        "cells": [
            {
                "key": c.key,
                "effect": c.true_effect,
                "artefact": c.artefact,
                "stratum": c.stratum,
                "replicates": c.replicates,
            }
            for c in cells
        ],
        "machine": platform.platform(),
        "summary": summarise(rows, scanned),
        "rows": rows,
    }
