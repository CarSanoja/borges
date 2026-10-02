from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

CASES_DIR = Path(__file__).resolve().parents[2] / "cases"
SHARED = CASES_DIR / "marp_shared"
if str(SHARED) not in sys.path:
    sys.path.insert(0, str(SHARED))

from marp_grid import read_grid  # noqa: E402
from marp_options import WB_OVERALL, defaults, option_codes, option_ids  # noqa: E402
from marp_validate import changed_steps, run_universe  # noqa: E402

from borges.cases.models import CaseSpec  # noqa: E402
from borges.cases.registry import CaseRegistry  # noqa: E402
from borges.runs.models import RunSnapshot  # noqa: E402
from borges.runs.state import fold  # noqa: E402

__all__ = [
    "WB_OVERALL",
    "changed_steps",
    "defaults",
    "option_codes",
    "option_ids",
    "read_grid",
    "run_universe",
]

CASE_IDS = {1: "marp_religiosity", 2: "marp_norms"}


def case_spec(rq: int) -> CaseSpec:
    return CaseRegistry(CASES_DIR).get(CASE_IDS[rq])


def case_frame(rq: int) -> pd.DataFrame:
    return pd.read_parquet(CASES_DIR / CASE_IDS[rq] / "data.parquet")


def recorded(rq: int) -> RunSnapshot:
    events = CaseRegistry(CASES_DIR).recording(CASE_IDS[rq])
    assert events
    return fold(events)
