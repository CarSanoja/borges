from __future__ import annotations

import sys
from collections.abc import Callable
from dataclasses import dataclass

MB = 1024 * 1024
DEFAULT_NPROC = 1024


@dataclass(frozen=True)
class ResourceLimits:
    memory_mb: int = 3072
    cpu_s: int = 600
    fsize_mb: int = 256
    nproc: int = DEFAULT_NPROC


def limit_pairs(limits: ResourceLimits, platform: str) -> list[tuple[str, int]]:
    pairs = [
        ("RLIMIT_CPU", limits.cpu_s),
        ("RLIMIT_FSIZE", limits.fsize_mb * MB),
        ("RLIMIT_NPROC", limits.nproc),
    ]
    if platform != "darwin":
        pairs.insert(0, ("RLIMIT_AS", limits.memory_mb * MB))
    return pairs


def make_preexec(limits: ResourceLimits, platform: str = sys.platform) -> Callable[[], None] | None:
    if not platform.startswith("linux"):
        return None
    import resource

    resolved = [(getattr(resource, name), value) for name, value in limit_pairs(limits, platform)]

    def apply() -> None:
        for which, value in resolved:
            resource.setrlimit(which, (value, value))

    return apply
