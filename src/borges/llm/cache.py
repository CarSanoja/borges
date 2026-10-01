from __future__ import annotations

import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import Any


def atomic_write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(content)
        os.replace(tmp_name, path)
    except BaseException:
        Path(tmp_name).unlink(missing_ok=True)
        raise


def cache_key(
    model: str,
    messages: list[dict[str, str]],
    schema_name: str | None,
    max_tokens: int,
    temperature: float,
) -> str:
    canonical = json.dumps(
        {
            "model": model,
            "messages": messages,
            "schema": schema_name,
            "max_tokens": max_tokens,
            "temperature": temperature,
        },
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


class DiskCache:
    """Content-addressed store of LLM records: model, text, parsed, tokens_in, tokens_out."""

    def __init__(self, directory: Path) -> None:
        self.directory = directory

    def _path(self, key: str) -> Path:
        return self.directory / f"{key}.json"

    def get(self, key: str) -> dict[str, Any] | None:
        path = self._path(key)
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError):
            return None
        return record if isinstance(record, dict) else None

    def put(self, key: str, record: dict[str, Any]) -> None:
        atomic_write_text(self._path(key), json.dumps(record, ensure_ascii=False))
