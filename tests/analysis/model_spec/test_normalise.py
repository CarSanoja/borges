from __future__ import annotations

from borges.analysis.model_spec.normalise import normalise_spec
from tests.analysis.model_spec.data import make_spec
from tests.analysis.model_spec.test_validate_exposure import PROFILE

AVAILABLE = ["redCards", "games", "skin_dark", "position", "leagueCountry", "height"]
TEXT = (
    "Poisson GLM: redCards ~ skin_dark + C(position) + C(leagueCountry) + height, offset "
    "log(games), standard errors clustered by referee."
)


def test_formula_terms_become_their_columns() -> None:
    spec = make_spec(
        "poisson",
        outcome="redCards",
        exposure="skin_dark",
        covariates=["C(position, drop_first=True)", "C(leagueCountry)", "height", "position"],
    )
    fixed = normalise_spec(spec, TEXT, AVAILABLE, None)
    assert fixed.covariates == ["position", "leagueCountry", "height"]


def test_an_exposure_set_to_the_offset_is_replaced_by_the_one_the_option_names() -> None:
    spec = make_spec(
        "poisson",
        outcome="redCards",
        exposure="games",
        offset_log="games",
        covariates=["skin_dark", "height"],
    )
    fixed = normalise_spec(spec, TEXT, AVAILABLE, None)
    assert fixed.exposure == "skin_dark" and fixed.covariates == ["height"]
    assert fixed.offset_log == "games"


def test_an_unnamed_exposure_stays_for_the_validator_to_refuse() -> None:
    spec = make_spec("poisson", outcome="redCards", exposure="games", offset_log="games")
    assert normalise_spec(spec, "a Poisson model", AVAILABLE, None) == spec


def test_an_unsupported_spec_is_untouched() -> None:
    spec = make_spec("ols", outcome="y_cont", exposure="treatment").model_copy(
        update={"supported": False}
    )
    assert (
        normalise_spec(spec, "treatment = (variant == 'treatment')", ["variant"], PROFILE) == spec
    )
