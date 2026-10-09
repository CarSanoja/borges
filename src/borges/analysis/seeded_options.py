"""Options the plan always has, whatever the planner proposed.

Rows that repeat a unit (a player in many dyads, a user in many sessions) are not independent, and
standard errors that ignore it are too narrow. The profile records each repeated unit; for every
one, the model step gets an option that fits the default model again with errors clustered by that
unit. The option is the default model's own code with the unit's name beside it, which the harness
reads to cluster the fit, so it needs no judge and no coder, and it is marked as pinned.
"""

from __future__ import annotations

import re

from borges.analysis.ids import slug_id
from borges.analysis.models import AnalysisPlan, Option, RepeatedUnit, Step

UNSUPPORTED = re.compile(r"\b(?:GEE|MixedLM|QuantReg|BayesMixed|Mixed)\b|mixedlm|quantreg", re.I)
CLUSTERS_ALREADY = re.compile(r"""cov_type\s*=\s*["']cluster["']""")


def cluster_option_id(unit: str) -> str:
    return f"cluster_{slug_id(unit)}"


def _model_step(plan: AnalysisPlan) -> Step | None:
    return next((s for s in reversed(plan.steps) if s.kind == "model"), None)


def _clusterable(default: Option) -> bool:
    code = default.code
    if code is None or "def estimate" not in code or default.cluster_by is not None:
        return False
    if "statsmodels" not in code:
        return False
    return UNSUPPORTED.search(code) is None and CLUSTERS_ALREADY.search(code) is None


def _named_in_metric(plan: AnalysisPlan, unit: RepeatedUnit) -> bool:
    return re.search(rf"\b{re.escape(unit.name)}\b", plan.decision_rule.metric) is not None


def cluster_option(default: Option, unit: RepeatedUnit) -> Option:
    return Option(
        id=cluster_option_id(unit.name),
        label=f"Cluster the errors by {unit.name}",
        rationale=(
            f"Rows repeat {unit.n_units:,} {unit.name} values, about {unit.rows_per_unit:g} rows "
            "each, so errors that treat rows as independent may be too narrow."
        ),
        spec=(
            f"{default.spec.rstrip('. ')}. Standard errors cluster-robust by {unit.name} "
            "(cov_type cluster); every other choice as in the default model."
        ),
        is_default=False,
        origin="pinned",
        code=default.code,
        cluster_by=unit.name,
    )


def seed_cluster_options(plan: AnalysisPlan) -> list[str]:
    """Add 'cluster by <unit>' to the model step for each repeated unit; return the new ids."""
    step = _model_step(plan)
    if step is None or not _clusterable(step.default):
        return []
    taken = {o.id for o in step.options}
    added: list[str] = []
    for unit in plan.dataset.repeated_units:
        option_id = cluster_option_id(unit.name)
        if option_id in taken or _named_in_metric(plan, unit):
            continue
        step.options.append(cluster_option(step.default, unit))
        added.append(option_id)
    return added
