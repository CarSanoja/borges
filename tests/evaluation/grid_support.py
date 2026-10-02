from __future__ import annotations

import io

from borges.analysis.models import AnalysisPlan
from tests.garden.test_engine_integration import make_frame, make_plan


def small_plan() -> tuple[AnalysisPlan, bytes]:
    frame = make_frame()
    full = make_plan(frame)
    plan = full.model_copy(
        update={"steps": [s for s in full.steps if s.id in {"internal", "model"}]}
    )
    buffer = io.BytesIO()
    frame.to_parquet(buffer)
    return plan, buffer.getvalue()
