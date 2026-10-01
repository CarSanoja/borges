from __future__ import annotations

from borges.analysis.models import AnalysisResult, Option, Step, StepTrace

DATA_FILE = "data.parquet"
STATE_DIR = "state"
TRACE_PREFIX = "BORGES_TRACE "
RESULT_PREFIX = "BORGES_RESULT "


def step_filename(step_id: str, option_id: str) -> str:
    raise NotImplementedError


def render_step(step: Step, option: Option) -> str:
    raise NotImplementedError


def step_command(step_id: str, option_id: str) -> list[str]:
    raise NotImplementedError


def parse_output(stdout: str) -> tuple[list[StepTrace], AnalysisResult | None]:
    raise NotImplementedError
