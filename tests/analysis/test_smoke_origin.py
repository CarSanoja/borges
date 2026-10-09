from __future__ import annotations

import numpy as np

from borges.analysis.smoke_orientation import orientation_error
from borges.analysis.smoke_origin import shifted_error
from tests.analysis.smoke_fakes import effects

DAYS = [float(7 + i % 19) for i in range(60)]


def test_a_count_moved_to_another_origin_is_named_by_how_far_it_moved() -> None:
    luteal = [d - 14 for d in DAYS]
    error = shifted_error("cycle_day", effects("cycle_day", DAYS), effects("cycle_day", luteal))
    assert error is not None
    assert "column 'cycle_day' follows the default option's one for one but sits -14.0" in error
    assert "Count from the default's origin" in error
    named = orientation_error(
        ["cycle_day"], effects("cycle_day", DAYS), effects("cycle_day", luteal)
    )
    assert named == error


def test_a_count_from_a_nearby_origin_passes() -> None:
    rng = np.random.default_rng(2)
    forward = [d - float(rng.integers(0, 4)) for d in DAYS]
    assert (
        shifted_error("cycle_day", effects("cycle_day", DAYS), effects("cycle_day", forward))
        is None
    )


def test_rescaled_and_standardised_columns_are_not_a_moved_origin() -> None:
    months = [12 * d for d in DAYS]
    mean, sd = float(np.mean(DAYS)), float(np.std(DAYS))
    zscores = [(d - mean) / sd for d in DAYS]
    for other in (months, zscores):
        assert shifted_error("x", effects("x", DAYS), effects("x", other)) is None
