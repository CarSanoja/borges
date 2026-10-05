from __future__ import annotations

from borges.analysis.narrative_ids import drop_option_ids
from tests.garden.synthetic import option, plan_of, step_of


def plan():
    return plan_of(
        step_of(
            "step_adjust",
            "feature",
            option("opt_adj_min", True, label="Age and gender only"),
            option("adv_opt_adj_full_demo", label="Country fixed effects"),
        ),
        step_of("model", "model", option("ols", True)),
    )


def test_a_parenthesised_part_of_an_option_id_is_dropped() -> None:
    text = "Adding country fixed effects (opt_adj_full_demo) also flips the verdict."
    assert drop_option_ids(plan(), text) == "Adding country fixed effects also flips the verdict."


def test_an_exact_id_becomes_the_label_or_the_title() -> None:
    text = "Switching to adv_opt_adj_full_demo at step_adjust flips it."
    out = drop_option_ids(plan(), text)
    assert out == 'Switching to "Country fixed effects" at Step step_adjust flips it.'


def test_a_column_name_in_parentheses_is_kept() -> None:
    text = "The outcome (wb_psych_mean) moves the estimate."
    assert drop_option_ids(plan(), text) == text


def test_a_parenthesised_universe_id_is_dropped() -> None:
    text = "The flipped universe (u_c8af06a403) estimates -0.0178."
    assert drop_option_ids(plan(), text) == "The flipped universe estimates -0.0178."


def test_a_universe_id_inside_or_outside_parentheses_is_dropped() -> None:
    text = "With B (u_12c11039f3, estimate 3.74). The flipped universe u_145df22797 estimates 6.4."
    want = "With B (estimate 3.74). The flipped universe estimates 6.4."
    assert drop_option_ids(plan(), text) == want
