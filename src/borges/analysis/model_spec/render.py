from __future__ import annotations

from borges.analysis.model_spec.render_design import covariate_lines, exog_lines, frame_lines
from borges.analysis.model_spec.render_fit import fit_lines, result_lines
from borges.analysis.model_spec.schema import ModelSpecOutput

HEADER = [
    "import numpy as np",
    "import pandas as pd",
    "import statsmodels.api as sm",
    "",
    "",
    "def estimate(df, ctx):",
]


TEMPLATE_MARK = "    exog = sm.add_constant(pd.concat(parts, axis=1), has_constant='add')"


def is_rendered(code: str | None) -> bool:
    return bool(code) and str(code).startswith("\n".join(HEADER)) and TEMPLATE_MARK in str(code)


def render_code(spec: ModelSpecOutput) -> str:
    lines = [
        *HEADER,
        *covariate_lines(spec),
        *frame_lines(spec),
        *exog_lines(spec),
        *fit_lines(spec),
        *result_lines(spec),
    ]
    return "\n".join(lines) + "\n"
