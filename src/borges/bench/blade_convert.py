from __future__ import annotations

import ast
import hashlib
import re
from dataclasses import dataclass, field

from pydantic import BaseModel

from borges.analysis.models import AnalysisPlan, Option, Step
from borges.bench.blade_rules import BladeRule
from borges.bench.blade_source import Kind
from borges.garden.models import Universe
from borges.runs.models import RunSnapshot

DESCRIPTION_CHARS = 140
ID_LIKE = re.compile(r"^(rownames|ind|index|id|uuid|unnamed.*)$", re.IGNORECASE)
WORD = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")


class Cvar(BaseModel):
    description: str
    columns: list[str]


class Submission(BaseModel):
    ivs: list[Cvar]
    dv: Cvar
    controls: list[Cvar]


@dataclass
class AgentAnalysis:
    universe_id: str
    kind: str
    choices: dict[str, str]
    signature: str
    cvars: Submission
    transform_code: str
    m_code: str
    items: dict[Kind, list[str]] = field(default_factory=dict)

    def submission_row(self) -> dict:
        controls = [
            {**c.model_dump(), "is_moderator": False, "moderator_on": ""}
            for c in self.cvars.controls
        ]
        return {
            "cvars": {
                "ivs": [c.model_dump() for c in self.cvars.ivs],
                "dv": self.cvars.dv.model_dump(),
                "controls": controls,
            },
            "transform_code": self.transform_code,
            "m_code": self.m_code,
        }


def referenced_columns(code: str, columns: set[str]) -> set[str]:
    try:
        literals = [n.value for n in ast.walk(ast.parse(code)) if isinstance(n, ast.Constant)]
    except SyntaxError:
        literals = re.findall(r"""["']([^"']+)["']""", code)
    found: set[str] = set()
    for literal in literals:
        if not isinstance(literal, str):
            continue
        if literal in columns:
            found.add(literal)
        elif any(mark in literal for mark in "~+*:"):
            found.update(w for w in WORD.findall(literal) if w in columns)
    return found


def _describe(column: str, columns: dict[str, str]) -> str:
    text = " ".join(columns.get(column, "").split()) or column
    if len(text) > DESCRIPTION_CHARS:
        text = text[:DESCRIPTION_CHARS].rsplit(" ", 1)[0]
    return text.rstrip(" .,;(")


def build_cvars(
    feature_codes: list[str], model_codes: list[str], rule: BladeRule, columns: dict[str, str]
) -> Submission | None:
    known = set(columns)
    in_features = set().union(set(), *(referenced_columns(c, known) for c in feature_codes))
    in_model = set().union(set(), *(referenced_columns(c, known) for c in model_codes))
    ivs = [c for c in rule.iv if c in in_features] or [c for c in rule.iv if c in in_model]
    dvs = [c for c in rule.dv if c in in_features | in_model]
    if not ivs or not dvs:
        return None
    reserved = {*rule.iv, *rule.dv}
    controls = sorted(
        c for c in in_features | in_model if c not in reserved and not ID_LIKE.match(c)
    )
    return Submission(
        ivs=[Cvar(description="; ".join(_describe(c, columns) for c in ivs), columns=ivs)],
        dv=Cvar(description="; ".join(_describe(c, columns) for c in dvs), columns=dvs),
        controls=[Cvar(description=_describe(c, columns), columns=[c]) for c in controls],
    )


def _chosen(plan: AnalysisPlan, universe: Universe) -> list[tuple[Step, Option]]:
    return [(step, step.option(universe.choices[step.id])) for step in plan.steps]


def _rename(code: str, old: str, new: str) -> str:
    return re.sub(rf"\bdef {old}\(", f"def {new}(", code)


def compose_code(chosen: list[tuple[Step, Option]]) -> tuple[str, str]:
    parts, calls, model_code = [], [], ""
    for step, option in chosen:
        code = option.code or ""
        if step.kind == "model":
            model_code = code
            continue
        name = f"apply_{step.id}"
        parts.append(_rename(code, "apply", name))
        calls.append(f"    df = {name}(df, ctx)")
    transform = "\n\n".join(parts) + "\n\n\ndef transform(df):\n    ctx = {}\n"
    transform += "\n".join(calls) + "\n    return df\n"
    model = _rename(model_code, "estimate", "estimate_model")
    model += "\n\ndef model(df, ctx=None):\n    return estimate_model(df, ctx or {})\n"
    return transform, model


def _signature(chosen: list[tuple[Step, Option]]) -> str:
    joined = "\n".join(f"{s.id}:{o.code or o.spec}" for s, o in chosen)
    return hashlib.sha256(joined.encode()).hexdigest()[:16]


def analyze_universe(
    plan: AnalysisPlan, universe: Universe, rule: BladeRule, columns: dict[str, str]
) -> AgentAnalysis | None:
    chosen = _chosen(plan, universe)
    features = [o.code or "" for st, o in chosen if st.kind != "model"]
    models_code = [o.code or "" for st, o in chosen if st.kind == "model"]
    cvars = build_cvars(features, models_code, rule, columns)
    if cvars is None:
        return None
    transform, model = compose_code(chosen)
    transforms = [f"{s.title}: {o.label}. {o.spec}" for s, o in chosen if s.kind != "model"]
    models = [o.label.strip() or o.spec for s, o in chosen if s.kind == "model"]
    items: dict[Kind, list[str]] = {
        "cvar": [
            *(f"IV: {c.description}." for c in cvars.ivs),
            f"DV: {cvars.dv.description}.",
            *(f"Control: {c.description}." for c in cvars.controls),
        ],
        "transform": transforms,
        "model": [m.strip().lower() for m in models],
    }
    return AgentAnalysis(
        universe.id,
        universe.kind,
        universe.choices,
        _signature(chosen),
        cvars,
        transform,
        model,
        items,
    )


def convert_snapshot(
    snapshot: RunSnapshot, rule: BladeRule, columns: dict[str, str]
) -> list[AgentAnalysis]:
    plan = snapshot.plan
    if plan is None:
        return []
    seen: set[str] = set()
    analyses: list[AgentAnalysis] = []
    for universe in snapshot.garden.finished():
        analysis = analyze_universe(plan, universe, rule, columns)
        if analysis is None or analysis.signature in seen:
            continue
        seen.add(analysis.signature)
        analyses.append(analysis)
    return analyses
