from __future__ import annotations

from borges.runs.pipeline_caveats import default_departures
from tests.analysis.fakes import make_plan


def test_a_replaced_default_is_named_as_a_departure_from_the_analysis() -> None:
    planned = make_plan()
    coded = planned.model_copy(deep=True)
    step = coded.steps[0]
    for option in step.options:
        option.is_default = option.id == step.options[1].id
    found = default_departures(planned, coded)
    assert len(found) == 1
    assert found[0].startswith("The starting point is not exactly your analysis")
    assert f"'{planned.steps[0].default.label}' could not run" in found[0]
    assert f"'{step.options[1].label}' was used instead" in found[0]


def test_unchanged_defaults_leave_no_caveat() -> None:
    planned = make_plan()
    assert default_departures(planned, planned.model_copy(deep=True)) == []
