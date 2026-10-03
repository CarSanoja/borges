from __future__ import annotations

import itertools
import json
from pathlib import Path
from typing import Any

import pandas as pd

CASE_DIR = Path(__file__).resolve().parent
STEP_ORDER = [
    "storms",
    "femininity",
    "damages",
    "strength",
    "interaction",
    "year_control",
    "model",
]
DEFAULTS = {
    "storms": "drop_top2",
    "femininity": "masfem",
    "damages": "linear_2015",
    "strength": "pressure",
    "interaction": "full",
    "year_control": "none",
    "model": "negbin",
}


def fixture_path(key: str, directory: Path | None = None) -> Path:
    return (directory or CASE_DIR / "fixtures") / f"{key.replace(':', '__')}.json"


def load_codes(directory: Path | None = None) -> dict[str, str]:
    codes: dict[str, str] = {}
    for path in sorted((directory or CASE_DIR / "fixtures").glob("coder__*.json")):
        key = path.stem.removeprefix("coder__")
        codes[key] = json.loads(path.read_text())["parsed"]["code"]
    return codes


def compile_function(code: str, name: str):
    namespace: dict[str, Any] = {}
    exec(compile(code, "<option>", "exec"), namespace)
    return namespace[name]


def run_universe(
    frame: pd.DataFrame, choices: dict[str, str], codes: dict[str, str]
) -> dict[str, Any]:
    state = frame
    ctx: dict[str, Any] = {}
    for step in STEP_ORDER[:-1]:
        state = compile_function(codes[f"{step}.{choices[step]}"], "apply")(state, ctx)
    return compile_function(codes[f"model.{choices['model']}"], "estimate")(state, ctx)


def single_flips(options: dict[str, list[str]]) -> list[dict[str, str]]:
    return [
        {**DEFAULTS, step: option_id}
        for step, ids in options.items()
        for option_id in ids
        if option_id != DEFAULTS[step]
    ]


def all_universes(options: dict[str, list[str]]) -> list[dict[str, str]]:
    return [
        dict(zip(STEP_ORDER, combo, strict=True))
        for combo in itertools.product(*(options[s] for s in STEP_ORDER))
    ]


def changed_steps(choices: dict[str, str]) -> list[str]:
    return [s for s in STEP_ORDER if choices[s] != DEFAULTS[s]]
