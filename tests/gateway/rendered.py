from __future__ import annotations

from borges.analysis.harness import render_step
from borges.analysis.models import Option, Step


def rendered_step(code: str, home: str | None = None, audit: str | None = None) -> str:
    option = Option(id="o1", label="l", rationale="r", spec="s", is_default=True, code=code)
    step = Step(id="s1", title="t", kind="model", description="d", options=[option])
    return render_step(step, option, home, audit)
