from __future__ import annotations

from borges.garden.models import Report
from borges.runs.pipeline_caveats import UNTESTED, report_caveats


def report(n_universes: int) -> Report:
    return Report.model_construct(n_universes=n_universes, n_failed=0, failed=[])


def test_a_run_with_only_the_default_analysis_says_it_did_not_test_robustness() -> None:
    assert UNTESTED in report_caveats(report(1), None, 0.0)


def test_a_run_with_alternatives_has_no_untested_caveat() -> None:
    assert UNTESTED not in report_caveats(report(5), None, 0.0)
