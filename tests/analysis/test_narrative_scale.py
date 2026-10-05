from __future__ import annotations

from borges.analysis.narrative_scale import drop_unit_readings, unit_readings
from borges.garden.models import Report
from tests.garden.synthetic import result

SCALE = (
    "The original analysis is a model of log1p(alldeaths), so its estimate 0.0243 is on the log "
    "scale: about 2.5% more alldeaths per unit of the exposure, not 0.0243 additional alldeaths."
)


def report() -> Report:
    return Report.model_validate(
        {
            "question": "q",
            "original_verdict": "NO CLEAR EVIDENCE",
            "original_result": result(0.0243, p=0.53),
            "minimal_flip": None,
            "influences": [],
            "robustness": 1.0,
            "n_universes": 38,
            "n_flipped": 0,
        }
    )


def test_a_log_estimate_read_as_additional_deaths_is_found_and_dropped() -> None:
    text = (
        "The original analysis estimated that a one-unit increase in femininity is associated "
        "with 0.024 additional expected deaths. Switching to log1p(deaths) keeps the verdict."
    )
    assert len(unit_readings(report(), text, SCALE)) == 1
    assert drop_unit_readings(report(), text, SCALE) == (
        "Switching to log1p(deaths) keeps the verdict."
    )


def test_a_sentence_on_the_log_scale_or_without_the_estimate_is_kept() -> None:
    text = (
        "The original estimate 0.0243 is on the log scale, about 2.5% more deaths per unit. "
        "A negative binomial model gives 5.11 additional deaths. It is more than zero."
    )
    assert unit_readings(report(), text, SCALE) == []


def test_nothing_is_found_when_the_estimate_is_on_the_metric() -> None:
    text = "The original analysis estimated 0.024 additional deaths."
    assert unit_readings(report(), text, None) == []
