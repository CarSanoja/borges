from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel

from borges.telemetry.hashing import sha256_json, sha256_text

PACKAGE_ROOT = Path(__file__).resolve().parents[1]


def schema_sha(schema: type[BaseModel] | None) -> str | None:
    return sha256_json(schema.model_json_schema()) if schema is not None else None


def prompt_sha(text: str | None) -> str | None:
    return sha256_text(text) if text is not None else None


def code_sha(patterns: tuple[str, ...], root: Path = PACKAGE_ROOT) -> str | None:
    if not patterns:
        return None
    files = sorted({path for pattern in patterns for path in root.glob(pattern)})
    entries = [
        [str(p.relative_to(root)), sha256_text(p.read_text(encoding="utf-8"))] for p in files
    ]
    return sha256_json(entries)
