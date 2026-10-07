from __future__ import annotations

import re

from borges.gateway.armor_hooks import ArmorBlocked
from borges.llm.client import LLMError

CATEGORY = re.compile(r"\.output carries (code\.\w+)")
ARMOR_RETRY = (
    "The security screen refused the code before it ran ({category}). {advice} Write the code "
    "again without it."
)
ADVICE = {
    "code.dynamic": (
        "Import every module at the top of the file and never call __import__, eval, exec, "
        "compile, or getattr on a module."
    ),
    "code.dunder": (
        "Never touch attributes that start and end with two underscores; use isinstance, str(), "
        "or the library's public API instead."
    ),
    "code.import": (
        "Import only numpy, pandas, scipy, statsmodels, sklearn, and the standard math and "
        "statistics modules; do not import system, network, or process modules."
    ),
    "code.subprocess": "Do not run processes or touch the operating system; use only df and ctx.",
    "code.open_abs": "Do not open files by path; the data arrives in df.",
    "code.network": "Do not use the network; the data arrives in df.",
    "code.shell_words": "Do not write shell commands; use only df and ctx.",
}
DEFAULT_ADVICE = "Use only the public API of pandas, numpy, scipy and statsmodels on df and ctx."


def armor_refusal(exc: LLMError) -> str | None:
    if not isinstance(exc, ArmorBlocked):
        return None
    found = CATEGORY.search(exc.reason)
    if found is None:
        return None
    category = found.group(1)
    return ARMOR_RETRY.format(category=category, advice=ADVICE.get(category, DEFAULT_ADVICE))
