from __future__ import annotations

from borges.analysis.model_spec.ctx_listed import without_ctx_listed
from borges.analysis.model_spec.schema import ModelSpecOutput

AVAILABLE = ["wb", "relig_z", "cnorm_z", "age", "gender", "country", "age_sq"]
CTX = ["age", "gender", "country"]


def spec(covariates: list[str], from_ctx: bool = True) -> ModelSpecOutput:
    return ModelSpecOutput(
        supported=True,
        family="ols",
        outcome="wb",
        exposure="relig_z",
        moderator="cnorm_z",
        covariates=covariates,
        covariates_from_ctx=from_ctx,
    )


def test_ctx_names_and_their_dummies_are_left_to_ctx() -> None:
    listed = ["age", "gender_female", "country_Austria", "country_United Kingdom", "age_sq", "z_x"]
    assert without_ctx_listed(spec(listed), CTX, AVAILABLE).covariates == ["age_sq", "z_x"]


def test_a_spec_that_does_not_read_ctx_keeps_its_list() -> None:
    listed = ["age", "gender_female"]
    assert without_ctx_listed(spec(listed, False), CTX, AVAILABLE).covariates == listed
