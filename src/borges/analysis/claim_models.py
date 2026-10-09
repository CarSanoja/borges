from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

ClaimKind = Literal["coefficient", "marginal", "ratio", "generic"]
Direction = Literal["positive", "negative", "none"]


class ClaimedResult(BaseModel):
    """What the user's analysis text says the result is, read from its words."""

    estimate: float | None = None
    kind: ClaimKind = "generic"
    p_operator: str | None = None
    p_value: float | None = None
    significant: bool | None = None
    ci_low: float | None = None
    ci_high: float | None = None
    direction: Direction | None = None
    quote: str = ""


class ClaimCheck(BaseModel):
    """The claimed result next to the one Borges reproduced."""

    claimed: ClaimedResult
    term: str | None = None
    reproduced_estimate: float
    reproduced_p_value: float
    reproduced_ci_low: float
    reproduced_ci_high: float
    n: int
    alpha: float
    agrees: bool | None = None
    differences: list[str] = Field(default_factory=list)
    same_scale: bool = False
    sentence: str = ""
