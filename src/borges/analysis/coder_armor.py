from __future__ import annotations

from borges.gateway.armor_hooks import ArmorBlocked
from borges.llm.client import LLMError

ARMOR_RETRY = (
    "The security screen refused the code before it ran ({reason}). Import every module at the "
    "top of the file and never call __import__, eval, exec, compile, or getattr on a module."
)


def armor_refusal(exc: LLMError) -> str | None:
    if isinstance(exc, ArmorBlocked) and exc.reason.endswith(".output carries code.dynamic"):
        return ARMOR_RETRY.format(reason=exc.reason)
    return None
