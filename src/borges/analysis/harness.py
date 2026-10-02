from __future__ import annotations

import json
import re
from pathlib import Path

from borges.analysis.harness_main import MAIN_TEMPLATE
from borges.analysis.models import AnalysisResult, Option, Step, StepTrace
from borges.analysis.path_scrub import scrub_paths

DATA_FILE = "data.parquet"
STATE_DIR = "state"
TRACE_PREFIX = "BORGES_TRACE "
RESULT_PREFIX = "BORGES_RESULT "
ERROR_PREFIX = "BORGES_ERROR "

STEPS_DIR = "steps"
_UNSAFE = re.compile(r"[^A-Za-z0-9_-]")
_POLICY_SOURCE = (Path(__file__).parent / "runtime_policy.py").read_text()
POLICY_PRELUDE = f"exec(compile({_POLICY_SOURCE!r}, '<borges-policy>', 'exec'))\n"


def _sanitise(identifier: str) -> str:
    return _UNSAFE.sub("_", identifier)


def step_filename(step_id: str, option_id: str) -> str:
    return f"{STEPS_DIR}/{_sanitise(step_id)}__{_sanitise(option_id)}.py"


def step_command(step_id: str, option_id: str) -> list[str]:
    return ["python", step_filename(step_id, option_id)]


def render_step(step: Step, option: Option) -> str:
    if option.code is None:
        raise ValueError(f"option '{option.id}' of step '{step.id}' has no code")
    main = (
        MAIN_TEMPLATE.replace("__STEP_ID__", json.dumps(step.id))
        .replace("__OPTION_ID__", json.dumps(option.id))
        .replace("__KIND__", json.dumps(step.kind))
    )
    return POLICY_PRELUDE + option.code.rstrip("\n") + "\n" + main


def _json_lines(stdout: str, prefix: str) -> list[dict[str, object]]:
    payloads: list[dict[str, object]] = []
    for line in stdout.splitlines():
        if not line.startswith(prefix):
            continue
        try:
            payload = json.loads(line[len(prefix) :])
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            payloads.append(payload)
    return payloads


def parse_output(stdout: str) -> tuple[list[StepTrace], AnalysisResult | None]:
    traces = [StepTrace.model_validate(p) for p in _json_lines(stdout, TRACE_PREFIX)]
    results = _json_lines(stdout, RESULT_PREFIX)
    result = AnalysisResult.model_validate(results[-1]) if results else None
    return traces, result


def parse_error(stdout: str) -> str | None:
    errors = _json_lines(stdout, ERROR_PREFIX)
    if not errors:
        return None
    error = errors[-1]
    head = f"{error.get('type', 'Error')}: {error.get('message', '')}"
    where = error.get("where")
    return scrub_paths(f"{head}\n{where}" if where else head)
