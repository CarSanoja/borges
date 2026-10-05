from __future__ import annotations

import json
import re
from pathlib import Path

from borges.analysis.code_guard_ctx import UNADJUSTED
from borges.analysis.code_guard_statsmodels import option_intent
from borges.analysis.harness_effects import EffectTrace
from borges.analysis.harness_main import MAIN_TEMPLATE
from borges.analysis.harness_missing_cut import compared_names, imputes, read_names
from borges.analysis.models import AnalysisResult, Option, Step, StepTrace
from borges.analysis.offset_intent import wants_offset
from borges.analysis.path_scrub import scrub_paths

DATA_FILE = "data.parquet"
STATE_DIR = "state"
TRACE_PREFIX = "BORGES_TRACE "
RESULT_PREFIX = "BORGES_RESULT "
ERROR_PREFIX = "BORGES_ERROR "

RESULT_KEYS = ("estimate", "ci_low", "ci_high", "p_value", "n")
STEPS_DIR = "steps"
_UNSAFE = re.compile(r"[^A-Za-z0-9_-]")
_POLICY_PARTS = (
    "runtime_policy_paths.py",
    "runtime_policy_config.py",
    "runtime_policy_access.py",
    "runtime_policy.py",
)
_SIBLING_IMPORT = re.compile(
    r"^from borges\.analysis\.runtime_policy_\w+ import (?:\([^)]*\)|[^\n]*)\n", re.MULTILINE
)
POLICY_SOURCE = "".join(
    _SIBLING_IMPORT.sub("", (Path(__file__).parent / name).read_text()) for name in _POLICY_PARTS
)
POLICY_CALL = "_borges_install_policy(None, None)"


def policy_prelude(home: str | None = None, audit_path: str | None = None) -> str:
    source = POLICY_SOURCE.replace(POLICY_CALL, f"_borges_install_policy({home!r}, {audit_path!r})")
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
    design_check: bool = True,
) -> str:
    if option.code is None:
        raise ValueError(f"option '{option.id}' of step '{step.id}' has no code")
    main = (
        MAIN_TEMPLATE.replace("__STEP_ID__", json.dumps(step.id))
        .replace("__OPTION_ID__", json.dumps(option.id))
        .replace("__KIND__", json.dumps(step.kind))
        .replace("__RESULT_KEYS__", repr(RESULT_KEYS))
        .replace("__SPLIT_HALF__", repr(split_half))
        .replace("__DESIGN_CHECK__", repr(design_check))
        .replace("__PRODUCES__", repr(list(step.produces)))
        .replace("__ADJUSTS__", repr(not UNADJUSTED.search(option_intent(option))))
        .replace("__READS__", repr(read_names(option.code)))
        .replace("__IMPUTES__", repr(imputes(option)))
        .replace("__COMPARED__", repr(compared_names(option.code)))
        .replace("__OFFSET__", repr(wants_offset(option)))
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
