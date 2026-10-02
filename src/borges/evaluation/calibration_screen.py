from __future__ import annotations

import json

import pandas as pd

from borges.analysis.models import AnalysisResult, DecisionRule
from borges.analysis.result_scale import apply_scale, detect_scale
from borges.evaluation.calibration_data import CASE_DIR

FIXTURES = CASE_DIR / "fixtures"


def _load(key: str) -> dict:
    return json.loads((FIXTURES / (key.replace(":", "__") + ".json")).read_text())["parsed"]


def case_rule() -> DecisionRule:
    return DecisionRule.model_validate(
        json.loads((CASE_DIR / "case.json").read_text())["decision_rule"]
    )


def default_analysis(frame: pd.DataFrame) -> AnalysisResult:
    plan = _load("planner")
    ctx: dict = {}
    data = frame.copy()
    for step in plan["steps"]:
        option = next(o["id"] for o in step["options"] if o["is_default"])
        namespace: dict = {}
        exec(_load(f"coder:{step['id']}.{option}")["code"], namespace)
        if step["kind"] == "model":
            raw = AnalysisResult(**namespace["estimate"](data, ctx))
            return apply_scale(raw, detect_scale(case_rule().metric))
        data = namespace["apply"](data, ctx)
    raise AssertionError("the plan has no model step")


def default_verdict(frame: pd.DataFrame) -> str:
    return case_rule().label(default_analysis(frame))
