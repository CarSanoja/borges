from __future__ import annotations

import fcntl
import hashlib
import hmac
import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from borges.config import Settings
from borges.telemetry.audit_record import GENESIS_HASH
from borges.telemetry.hashing import canonical_json

SIGNED = "hmac-sha256"
UNSIGNED = "sha256"
SCHEMA = 1


@dataclass(frozen=True)
class AnchorConfig:
    path: Path
    key: str | None
    every: int


class Anchor(BaseModel):
    v: int = SCHEMA
    count: int
    head_hash: str
    ts: float
    prev: str = GENESIS_HASH
    alg: str = UNSIGNED
    mac: str = ""


def anchor_path_for(log_path: Path) -> Path:
    return log_path.with_name(log_path.stem + ".anchor.jsonl")


def anchor_config(settings: Settings, log_path: Path) -> AnchorConfig:
    return AnchorConfig(
        anchor_path_for(log_path),
        settings.borges_audit_anchor_key,
        settings.borges_audit_anchor_every,
    )


def _digest(anchor: Anchor, key: str | None) -> str:
    body = canonical_json(anchor.model_dump(mode="json", exclude={"mac"})).encode("utf-8")
    if key:
        return hmac.new(key.encode("utf-8"), body, hashlib.sha256).hexdigest()
    return hashlib.sha256(body).hexdigest()


def read_anchors(path: Path) -> list[Anchor]:
    if not Path(path).is_file():
        return []
    lines = Path(path).read_text(encoding="utf-8").splitlines()
    return [Anchor.model_validate(json.loads(line)) for line in lines if line.strip()]


def latest_anchor(path: Path) -> Anchor | None:
    try:
        anchors = read_anchors(path)
    except ValueError:
        return None
    return anchors[-1] if anchors else None


def write_anchor(config: AnchorConfig, count: int, head_hash: str) -> Anchor:
    config.path.parent.mkdir(parents=True, exist_ok=True)
    with config.path.open("a+", encoding="utf-8") as handle:
        fcntl.flock(handle, fcntl.LOCK_EX)
        handle.seek(0)
        lines = [line for line in handle.read().splitlines() if line.strip()]
        prev = json.loads(lines[-1]).get("mac", GENESIS_HASH) if lines else GENESIS_HASH
        draft = Anchor(
            count=count,
            head_hash=head_hash,
            ts=time.time(),
            prev=prev,
            alg=SIGNED if config.key else UNSIGNED,
        )
        anchor = draft.model_copy(update={"mac": _digest(draft, config.key)})
        handle.write(canonical_json(anchor.model_dump(mode="json")) + "\n")
        handle.flush()
    return anchor


def anchor_problem(
    anchors: list[Anchor], key: str | None, key_name: str = "BORGES_AUDIT_ANCHOR_KEY"
) -> str | None:
    prev = GENESIS_HASH
    for index, anchor in enumerate(anchors, start=1):
        if anchor.alg == SIGNED and not key:
            return f"the anchor is signed but {key_name} is not set"
        if key and anchor.alg != SIGNED:
            return f"anchor {index} is not signed although {key_name} is set"
        if not hmac.compare_digest(
            anchor.mac, _digest(anchor, key if anchor.alg == SIGNED else None)
        ):
            return f"anchor {index} signature does not match its content"
        if anchor.prev != prev:
            return f"anchor {index} does not follow the previous anchor (an anchor was removed)"
        prev = anchor.mac
    return None


def hashes_at(log_path: Path, wanted: set[int]) -> tuple[dict[int, str], int]:
    found: dict[int, str] = {}
    total = 0
    for raw in Path(log_path).read_text(encoding="utf-8").splitlines():
        if not raw.strip():
            continue
        total += 1
        record: Any = json.loads(raw)
        if record["seq"] in wanted:
            found[record["seq"]] = record["hash"]
    return found, total
