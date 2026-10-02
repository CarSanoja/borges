from __future__ import annotations

import hashlib
import hmac
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from borges.identity.store_key import notice_for
from borges.telemetry.hashing import canonical_json, sha256_text

HASH_FIELDS = ("prev_hash", "hash")


class ChainBroken(RuntimeError):
    def __init__(self, path: Path, line: int, reason: str) -> None:
        self.path = Path(path)
        self.line = line
        self.reason = reason
        super().__init__(
            f"{self.path} failed hash-chain verification at line {line}: {reason}. "
            "The file was edited or truncated; refusing to use it."
        )


@dataclass(frozen=True)
class ChainStatus:
    ok: bool
    records: int
    head_hash: str
    legacy: int = 0
    broken_line: int | None = None
    reason: str | None = None
    keyed: bool = False
    anchored: bool = False

    @property
    def notice(self) -> str:
        return notice_for(self.keyed)


def link_hash(body: dict[str, Any], prev_hash: str, key: str | None = None) -> str:
    text = canonical_json({**body, "prev_hash": prev_hash})
    if key:
        return hmac.new(key.encode("utf-8"), text.encode("utf-8"), hashlib.sha256).hexdigest()
    return sha256_text(text)


def body_of(record: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in record.items() if k not in HASH_FIELDS}


def split_torn(text: str) -> tuple[str, str]:
    if not text or text.endswith("\n"):
        return text, ""
    cut = text.rfind("\n") + 1
    partial = text[cut:]
    try:
        if isinstance(json.loads(partial), dict):
            return text, ""
    except ValueError:
        pass
    return text[:cut], partial
