from __future__ import annotations

from pathlib import Path

from borges.telemetry.audit_anchor import SIGNED, anchor_path_for, read_anchors

KEYED_NO_KEY = "keyed store, key not available"
HINT = (
    "set BORGES_STORE_KEY (or point BORGES_HOME at the home that holds identity/store.key); "
    "this is not evidence of tampering"
)


def signed_anchors(anchor_path: Path) -> bool:
    try:
        return any(anchor.alg == SIGNED for anchor in read_anchors(anchor_path))
    except (OSError, ValueError):
        return False


def keyed_without_key(log_path: Path, held: str | None) -> bool:
    if held:
        return False
    return signed_anchors(anchor_path_for(Path(log_path)))


def keyed_message(log_path: Path) -> str:
    return (
        f"{KEYED_NO_KEY}: {log_path.name} is signed with a key this process does not hold; {HINT}"
    )


def broken_message(path: Path, default: str, held: str | None) -> str:
    return keyed_message(path) if keyed_without_key(path, held) else default
