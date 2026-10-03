from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from borges.identity.scopes import ADMIN, LEGACY_TOKEN_SCOPES, PUBLIC_SCOPES

PrincipalKind = Literal["anonymous", "key", "legacy"]

CALLER_PREFIX = "caller://"
ANONYMOUS_ID = f"{CALLER_PREFIX}anonymous"
LEGACY_ID = f"{CALLER_PREFIX}legacy-live-token"


RESERVED_KEY_NAMES = frozenset(
    {"anonymous", "legacy-live-token", "public-demo", "named-public-demo"}
)


def caller_principal(name: str) -> str:
    return f"{CALLER_PREFIX}{name}"


@dataclass(frozen=True)
class Principal:
    id: str
    kind: PrincipalKind
    scopes: frozenset[str]
    key_id: str | None = None
    expires_at: float | None = None

    def has(self, scope: str) -> bool:
        return scope in self.scopes or ADMIN in self.scopes

    def has_any(self, scopes: tuple[str, ...]) -> bool:
        return any(self.has(scope) for scope in scopes)

    @property
    def anonymous(self) -> bool:
        return self.kind == "anonymous"


ANONYMOUS = Principal(id=ANONYMOUS_ID, kind="anonymous", scopes=PUBLIC_SCOPES)
LEGACY = Principal(id=LEGACY_ID, kind="legacy", scopes=PUBLIC_SCOPES | LEGACY_TOKEN_SCOPES)
