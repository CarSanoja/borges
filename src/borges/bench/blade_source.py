from __future__ import annotations

import csv
import json
import os
import sys
from pathlib import Path
from typing import Literal

import pandas as pd
from pydantic import BaseModel, Field

BLADE_ENV = "BORGES_BLADE_DIR"
INSTALL_HINT = (
    "BLADE data not found. Clone https://github.com/behavioral-data/BLADE and pass "
    f"--blade-dir <clone> (or set {BLADE_ENV}). Code Apache-2.0, data ODC-By 1.0."
)
Kind = Literal["cvar", "transform", "model"]


class BladeNotFound(RuntimeError):
    pass


class ExpertItem(BaseModel):
    kind: Kind
    text: str
    var_type: str | None = None


class BladeDataset(BaseModel):
    id: str
    research_question: str
    columns: dict[str, str]
    num_rows: int
    csv_path: Path
    expert: list[ExpertItem] = Field(default_factory=list)

    def items(self, kind: Kind) -> list[str]:
        return [item.text for item in self.expert if item.kind == kind]


def resolve_root(explicit: Path | None = None) -> Path:
    given = explicit or (Path(os.environ[BLADE_ENV]) if os.environ.get(BLADE_ENV) else None)
    if given is None:
        raise BladeNotFound(INSTALL_HINT)
    nested = given / "blade_bench" / "datasets"
    root = nested if nested.is_dir() else given
    if not root.is_dir():
        raise BladeNotFound(f"{INSTALL_HINT} Looked in {given}.")
    return root


def annotated_ids(root: Path) -> list[str]:
    return sorted(
        path.name
        for path in root.iterdir()
        if all((path / name).is_file() for name in ("info.json", "data.csv", "annotations.csv"))
    )


def _cell(row: dict[str, str], key: str) -> dict | None:
    raw = (row.get(key) or "").strip()
    if not raw:
        return None
    parsed = json.loads(raw)
    return parsed if isinstance(parsed, dict) else None


def _cvar_text(spec: dict) -> str:
    kind, concept = spec.get("variable_type", "Control"), spec.get("concept", "")
    if kind != "Control":
        return f"{kind}: {concept}"
    if spec.get("interaction"):
        return f"Moderator: {concept} interacting with {spec.get('on', '')} variable"
    return f"Control: {concept}."


def parse_expert(annotations: Path) -> list[ExpertItem]:
    csv.field_size_limit(sys.maxsize)
    seen: set[tuple[str, str]] = set()
    items: list[ExpertItem] = []

    def add(kind: Kind, text: str, var_type: str | None = None) -> None:
        key = (kind, text.strip().lower())
        if text.strip() and key not in seen:
            seen.add(key)
            items.append(ExpertItem(kind=kind, text=text.strip(), var_type=var_type))

    with annotations.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            if spec := _cell(row, "conceptual_spec_json"):
                add("cvar", _cvar_text(spec), spec.get("variable_type"))
            spec = _cell(row, "transform_spec_json")
            if spec and spec.get("spec_name") != "ROOT" and spec.get("specification"):
                code = str(spec.get("code", "")).strip()
                text = f"{spec['specification']} ({code})" if code else spec["specification"]
                add("transform", text)
            if spec := _cell(row, "model_spec_json"):
                add("model", str(spec.get("specification", "")).strip().lower())
    return items


def load_dataset(root: Path, dataset_id: str) -> BladeDataset:
    directory = root / dataset_id
    if not (directory / "info.json").is_file():
        raise BladeNotFound(f"dataset '{dataset_id}' is not in {root}")
    info = json.loads((directory / "info.json").read_text(encoding="utf-8"))
    fields = info["data_desc"]["fields"]
    columns = {f["column"]: str(f["properties"].get("description", "")).strip() for f in fields}
    return BladeDataset(
        id=dataset_id,
        research_question=" ".join(info["research_questions"]).strip(),
        columns=columns,
        num_rows=int(info["data_desc"].get("num_rows") or 0),
        csv_path=directory / "data.csv",
        expert=parse_expert(directory / "annotations.csv"),
    )


def read_frame(dataset: BladeDataset) -> pd.DataFrame:
    return pd.read_csv(dataset.csv_path)
