from __future__ import annotations

import json
import re
from pathlib import Path

from borges.analysis.harness_effects import EffectTrace
from borges.analysis.harness_main import MAIN_TEMPLATE
from borges.analysis.models import AnalysisResult, Option, Step, StepTrace
from borges.analysis.path_scrub import scrub_paths

DATA_FILE = "data.parquet"
STATE_DIR = "state"
TRACE_PREFIX = "BORGES_TRACE "
RESULT_PREFIX = "BORGES_RESULT "
ERROR_PREFIX = "BORGES_ERROR "

RESULT_KEYS = ("estimate", "ci_low", "ci_high", "p_value", "n")
STEPS_DIR = "steps"
_UNSAFE = re.compile(r"[^A-Za-z0-9_-]")
_POLICY_PARTS = ("runtime_policy_paths.py", "runtime_policy_config.py", "runtime_policy.py")
_SIBLING_IMPORT = re.compile(
    r"^from borges\.analysis\.runtime_policy_\w+ import (?:\([^)]*\)|[^\n]*)\n", re.MULTILINE
)
_POLICY_SOURCE = "".join(
    _SIBLING_IMPORT.sub("", (Path(__file__).parent / name).read_text()) for name in _POLICY_PARTS
)
_POLICY_CALL = "_borges_install_policy(None, None)"


def policy_prelude(home: str | None = None, audit_path: str | None = None) -> str:
    source = _POLICY_SOURCE.replace(
        _POLICY_CALL, f"_borges_install_policy({home!r}, {audit_path!r})"
    )
    return f"exec(compile({source!r}, '<borges-policy>', 'exec'), {{}})\n"


def _sanitise(identifier: str) -> str:
    return _UNSAFE.sub("_", identifier)


def step_filename(step_id: str, option_id: str) -> str:
    return f"{STEPS_DIR}/{_sanitise(step_id)}__{_sanitise(option_id)}.py"


def step_command(step_id: str, option_id: str) -> list[str]:
    return ["python", step_filename(step_id, option_id)]


def render_step(
    step: Step,
    option: Option,
    policy_home: str | None = None,
    policy_audit_path: str | None = None,
    split_half: bool = False,
) -> str:
    if option.code is None:
        raise ValueError(f"option '{option.id}' of step '{step.id}' has no code")
    main = (
        MAIN_TEMPLATE.replace("__STEP_ID__", json.dumps(step.id))
        .replace("__OPTION_ID__", json.dumps(option.id))
        .replace("__KIND__", json.dumps(step.kind))
        .replace("__RESULT_KEYS__", repr(RESULT_KEYS))
        .replace("__SPLIT_HALF__", repr(split_half))
        .replace("__PRODUCES__", repr(list(step.produces)))
    )
    return policy_prelude(policy_home, policy_audit_path) + option.code.rstrip("\n") + "\n" + main


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
    traces: list[StepTrace] = [
        EffectTrace.model_validate(p) for p in _json_lines(stdout, TRACE_PREFIX)
    ]
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
