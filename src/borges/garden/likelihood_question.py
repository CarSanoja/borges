"""A question about how likely something is, answered on a count or an amount.

"Are more religious women less likely to have affairs?" was answered on the number of affairs
(77 distinct values, median 0) by every universe of r_20261009T003732_8fbd3d (r11, G10): a lower
average count is not a lower chance of any, and the report did not say which one it measured.
"""

from __future__ import annotations

import re

from borges.analysis.models import AnalysisPlan, ColumnProfile
from borges.garden.models import Garden

LIKELIHOOD = re.compile(
    r"\b(?:likel(?:y|ihood)|probabilit\w*|probabl[ey]|chances?|odds|propens\w*|"
    r"probabilidad\w*|propens[oa]s?)\b",
    re.I,
)
BINARY_VALUES = 2


def _outcome(garden: Garden) -> str | None:
    baseline = garden.universes.get(garden.baseline_id or "")
    if baseline is None:
        return None
    for trace in reversed(baseline.traces):
        name = (trace.design or {}).get("outcome")
        if isinstance(name, str) and name:
            return name
    return None


def _column(plan: AnalysisPlan, name: str) -> ColumnProfile | None:
    return next((c for c in plan.dataset.columns if c.name == name), None)


def likelihood_caveats(plan: AnalysisPlan, garden: Garden) -> list[str]:
    asked = LIKELIHOOD.search(plan.question)
    name = _outcome(garden) if asked else None
    column = _column(plan, name) if name else None
    if asked is None or column is None or column.n_unique <= BINARY_VALUES:
        return []
    zero = column.summary.get("min") == 0
    define = f"for example {name} > 0" if zero else f"a yes/no version of {name}"
    return [
        f'The question asks how likely something is ("{asked.group(0)}"), but the original '
        f"analysis models {name}, which takes {column.n_unique} values, so its estimate is a "
        f"change in the average {name}, not in the chance of any. To answer the question as "
        f"asked, model a yes/no outcome ({define})."
    ]
