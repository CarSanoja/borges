from __future__ import annotations

from borges.analysis.models import Option
from borges.analysis.smoke_default_encoding import model_fault

AVAILABLE = " | columns available (4): ['games', 'position', 'country', 'dark']; ctx keys: []"
POSITION = "KeyError: ['position_Center Back', 'position_Goalkeeper']" + AVAILABLE


def option(code: str, spec: str = "Adjust for games and position.") -> Option:
    return Option(id="o", label="l", rationale="r", spec=spec, code=code)


def test_dummy_names_the_model_made_are_its_own_fault() -> None:
    chosen = option("def apply(df, ctx):\n    ctx['covariates'] = ['games', 'position']\n")
    assert model_fault(POSITION, chosen)


def test_dummies_the_upstream_option_promised_are_its_fault() -> None:
    spec = "Set ctx['covariates'] = ['age'] + [f'country_{i}' for i in range(1, 24)]."
    error = "KeyError: ['country_1', 'country_2']" + AVAILABLE
    assert not model_fault(error, option("", spec))


def test_a_column_the_data_lacks_is_the_upstream_option_s_fault() -> None:
    chosen = option("def apply(df, ctx):\n    ctx['covariates'] = ['group']\n")
    assert not model_fault("KeyError: ['group']" + AVAILABLE, chosen)
    assert not model_fault("KeyError: ['position_Center Back', 'group']" + AVAILABLE, chosen)


def test_text_columns_stay_the_model_s_fault() -> None:
    assert model_fault("ValueError: could not convert string to float: 'England'", option(""))
