from __future__ import annotations

import itertools
import json
from pathlib import Path
from typing import Any

import pandas as pd
from marp_options import defaults, option_codes, option_ids, step_order


def compile_function(code: str, name: str):
    namespace: dict[str, Any] = {}
    exec(compile(code, "<option>", "exec"), namespace)
    return namespace[name]


def run_universe(
    frame: pd.DataFrame, rq: int, choices: dict[str, str], codes: dict[str, str] | None = None
) -> dict[str, Any]:
    codes = codes or option_codes(rq)
    state, ctx = frame, {}
    for step in step_order(rq)[:-1]:
        state = compile_function(codes[f"{step}.{choices[step]}"], "apply")(state, ctx)
    return compile_function(codes[f"model.{choices['model']}"], "estimate")(state, ctx)


def all_universes(rq: int) -> list[dict[str, str]]:
    order = step_order(rq)
    ids = option_ids(rq)
    return [
        dict(zip(order, combo, strict=True))
        for combo in itertools.product(*(ids[s] for s in order))
    ]


def changed_steps(rq: int, choices: dict[str, str]) -> list[str]:
    base = defaults(rq)
    return [s for s in step_order(rq) if choices[s] != base[s]]


def load_fixture_codes(directory: Path) -> dict[str, str]:
    codes: dict[str, str] = {}
    for path in sorted(directory.glob("coder__*.json")):
        codes[path.stem.removeprefix("coder__")] = json.loads(path.read_text())["parsed"]["code"]
    return codes
