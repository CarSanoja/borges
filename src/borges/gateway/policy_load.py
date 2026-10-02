from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from pydantic import ValidationError

from borges.config import Settings
from borges.gateway.errors import PolicyError
from borges.gateway.policy_models import AgentPolicy, GatewayPolicy
from borges.telemetry.hashing import sha256_json


@dataclass(frozen=True)
class LoadedPolicy:
    policy: GatewayPolicy
    sha: str
    path: Path

    def agent(self, agent_id: str) -> AgentPolicy | None:
        return self.policy.agents.get(agent_id)


_CACHE: dict[tuple[Path, int, int], LoadedPolicy] = {}


def parse_policy(text: str, path: Path) -> LoadedPolicy:
    try:
        policy = GatewayPolicy.model_validate_json(text)
    except ValidationError as exc:
        problems = "; ".join(
            f"{'.'.join(str(p) for p in e['loc'])}: {e['msg']}" for e in exc.errors()
        )
        raise PolicyError(f"gateway policy {path} is invalid: {problems}") from exc
    return LoadedPolicy(policy, sha256_json(policy.model_dump(mode="json")), path)


def load_policy(path: Path) -> LoadedPolicy:
    try:
        stat = path.stat()
        key = (path, stat.st_mtime_ns, stat.st_size)
        if key in _CACHE:
            return _CACHE[key]
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise PolicyError(f"gateway policy {path} cannot be read: {exc.strerror or exc}") from exc
    try:
        json.loads(text)
    except json.JSONDecodeError as exc:
        raise PolicyError(f"gateway policy {path} is not valid JSON: {exc}") from exc
    loaded = parse_policy(text, path)
    _CACHE.clear()
    _CACHE[key] = loaded
    return loaded


def policy_for(settings: Settings) -> LoadedPolicy:
    return load_policy(Path(settings.borges_gateway_policy))
