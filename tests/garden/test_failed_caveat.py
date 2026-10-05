from __future__ import annotations

from borges.garden.failed_caveat import failed_caveat
from tests.garden.synthetic import garden_of, option, plan_of, result, step_of, universe

PLAN = plan_of(
    step_of("cov", "feature", option("min", True), option("ref", label="Add referee country")),
    step_of("tone", "transform", option("med", True), option("half")),
    step_of(
        "m",
        "model",
        option("logit", True, label="Logit"),
        option("pois", label="Poisson"),
    ),
)


def failed(changes: dict[str, str], error: str):
    item = universe(PLAN, changes, result(0.1))
    item.status, item.result, item.verdict, item.error = "failed", None, None, error
    return item


def test_the_caveat_names_the_failing_options_their_errors_and_the_shared_choice() -> None:
    garden = garden_of(
        PLAN,
        universe(PLAN, {}, result(0.3)),
        failed({"cov": "ref"}, "m/logit: LinAlgError: Singular matrix\n  File x"),
        failed({"cov": "ref", "tone": "half"}, "m/logit: LinAlgError: Singular matrix"),
        failed({"cov": "ref", "tone": "half", "m": "pois"}, "m/pois: exit code -1"),
    )
    assert failed_caveat(PLAN, garden) == (
        "3 universes could not run and are left out of the robustness figure: failed 2 in "
        "'Logit' (LinAlgError: Singular matrix); 1 in 'Poisson' (the process was stopped, exit "
        "code -1). Every one of them uses 'Add referee country'."
    )


def test_one_failure_and_excluded_universes() -> None:
    garden = garden_of(
        PLAN,
        universe(PLAN, {}, result(0.3)),
        failed({"tone": "half"}, "tone/half: KeyError: 'x'"),
        failed({"m": "pois"}, "implausible estimate: 1e9 is far outside"),
    )
    assert failed_caveat(PLAN, garden) == (
        "1 universe could not run and is left out of the robustness figure: failed 1 in "
        "'label half' (KeyError: 'x')."
    )
    assert failed_caveat(PLAN, garden_of(PLAN, universe(PLAN, {}, result(0.3)))) is None
