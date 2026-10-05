from __future__ import annotations

import json

from borges.analysis import harness
from borges.analysis.model_spec.validate_standardized import reads_standardised
from borges.runs.models import RunSnapshot

SCRIPT_TEMPLATE = '''#!/usr/bin/env python3
"""Borges: universe __UNIVERSE__ of run __RUN__.

Re-executes every analysis step of this universe, in order, on a parquet dataset
and prints the result. Needs python with pandas, numpy, scipy and statsmodels.
Usage: python __FILE__ --data path/to/data.parquet
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile

PAYLOAD = json.loads(__PAYLOAD__)


def label(result):
    rule = PAYLOAD["decision_rule"]
    beyond = result["estimate"] > rule["threshold"]
    if rule["comparator"] == "lt":
        beyond = result["estimate"] < rule["threshold"]
    positive = beyond and result["p_value"] < rule["alpha"]
    return rule["positive_label"] if positive else rule["negative_label"]


def run_steps(data_path):
    work = tempfile.mkdtemp(prefix="borges_")
    try:
        shutil.copyfile(data_path, os.path.join(work, "data.parquet"))
        os.makedirs(os.path.join(work, "steps"))
        result = None
        for step in PAYLOAD["steps"]:
            target = os.path.join(work, step["filename"])
            with open(target, "w") as handle:
                handle.write(step["source"])
            proc = subprocess.run(
                [sys.executable, step["filename"]], cwd=work, capture_output=True, text=True
            )
            if proc.returncode != 0:
                sys.stderr.write(proc.stdout + proc.stderr)
                sys.exit("step " + step["id"] + " failed")
            for line in proc.stdout.splitlines():
                if line.startswith("BORGES_RESULT "):
                    result = json.loads(line[len("BORGES_RESULT "):])
            print("ran " + step["id"] + " / " + step["option"])
        return result
    finally:
        shutil.rmtree(work, ignore_errors=True)


def main():
    parser = argparse.ArgumentParser(description="Reproduce one Borges universe.")
    parser.add_argument("--data", required=True, help="parquet dataset the run analysed")
    args = parser.parse_args()
    result = run_steps(args.data)
    if result is None:
        sys.exit("the last step produced no result")
    print("question: " + PAYLOAD["question"])
    print(
        "estimate %.4f  CI [%.4f, %.4f]  p=%.4g  n=%d"
        % (result["estimate"], result["ci_low"], result["ci_high"], result["p_value"], result["n"])
    )
    print("verdict: " + label(result))
    recorded = PAYLOAD["recorded"]
    if recorded:
        print(
            "recorded in the run: estimate %.4f, verdict %s (identical on the original dataset)"
            % (recorded["estimate"], recorded["verdict"])
        )


main()
'''


def build_script(snapshot: RunSnapshot, universe_id: str, filename: str) -> str:
    plan = snapshot.plan
    if plan is None:
        raise KeyError(universe_id)
    universe = snapshot.garden.universes[universe_id]
    steps = []
    for step in plan.steps:
        option = step.option(universe.choices.get(step.id, step.default.id))
        steps.append(
            {
                "id": step.id,
                "option": option.id,
                "filename": harness.step_filename(step.id, option.id),
                "source": harness.render_step(
                    step, option, standardised=reads_standardised(plan.decision_rule.metric)
                ),
            }
        )
    recorded = (
        {"estimate": universe.result.estimate, "verdict": universe.verdict}
        if universe.result is not None
        else None
    )
    payload = {
        "question": snapshot.question or plan.question,
        "decision_rule": plan.decision_rule.model_dump(mode="json"),
        "steps": steps,
        "recorded": recorded,
    }
    return (
        SCRIPT_TEMPLATE.replace("__UNIVERSE__", universe_id)
        .replace("__RUN__", snapshot.run_id)
        .replace("__FILE__", filename)
        .replace("__PAYLOAD__", repr(json.dumps(payload)))
    )
