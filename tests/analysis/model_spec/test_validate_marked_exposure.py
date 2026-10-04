from __future__ import annotations

from borges.analysis.model_spec.validate_marked_exposure import (
    marked_exposure,
    marked_exposure_problems,
)
from borges.analysis.models import ColumnProfile, DatasetProfile
from tests.analysis.model_spec.data import make_spec


def profile(campaign_note: str | None) -> DatasetProfile:
    columns = [
        ColumnProfile(name="y", dtype="int64", n_missing=0, n_unique=2, note="the outcome"),
        ColumnProfile(name="campaign", dtype="int64", n_missing=0, n_unique=48, note=campaign_note),
        ColumnProfile(name="contact", dtype="object", n_missing=12981, n_unique=2),
    ]
    return DatasetProfile(name="bank", n_rows=45211, columns=columns)


BANK = profile("number of contacts in this campaign; the exposure of interest")


def test_a_spec_on_another_column_than_the_marked_exposure_is_refused() -> None:
    spec = make_spec("logit", outcome="y", exposure="contact", exposure_level="cellular")
    [problem] = marked_exposure_problems(spec, BANK)
    assert "'campaign'" in problem and "'contact'" in problem


def test_the_marked_exposure_and_a_column_built_from_it_pass() -> None:
    assert marked_exposure(BANK) == "campaign"
    for exposure in ("campaign", "campaign_w"):
        spec = make_spec("logit", outcome="y", exposure=exposure)
        assert marked_exposure_problems(spec, BANK) == []


def test_without_a_marked_column_nothing_is_checked() -> None:
    spec = make_spec("logit", outcome="y", exposure="contact", exposure_level="cellular")
    assert marked_exposure(profile(None)) is None
    assert marked_exposure_problems(spec, profile(None)) == []
