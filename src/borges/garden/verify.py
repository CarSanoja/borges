from __future__ import annotations

from borges.analysis.models import AnalysisPlan
from borges.garden.models import Flip, Garden
from borges.sandbox.backend import BranchBackend


async def verify_flip(
    backend: BranchBackend, plan: AnalysisPlan, data: bytes, flip: Flip, garden: Garden
) -> Flip:
    raise NotImplementedError
