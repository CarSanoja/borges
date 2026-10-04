from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

Family = Literal["ols", "logit", "poisson", "quasipoisson", "negbin"]
CovType = Literal["nonrobust", "HC0", "HC1", "HC2", "HC3", "cluster", "gee"]
GROUPED = ("cluster", "gee")
GEE_FAMILIES = {"ols": "Gaussian", "logit": "Binomial", "poisson": "Poisson"}
Report = Literal["coefficient", "odds_ratio", "rate_ratio", "marginal_effect"]

INTERACTION_COLUMN = "exposure_by_moderator"
RESERVED_COLUMNS = frozenset({INTERACTION_COLUMN, "const"})


class ModelSpecOutput(BaseModel):
    supported: bool
    reason: str = ""
    family: Family | None = None
    outcome: str | None = None
    exposure: str | None = None
    exposure_level: str | None = None
    moderator: str | None = None
    covariates: list[str] = Field(default_factory=list)
    covariates_from_ctx: bool = False
    offset_log: str | None = None
    cov_type: CovType = "nonrobust"
    cluster: str | None = None
    standardize: list[str] = Field(default_factory=list)
    report: Report = "coefficient"
