from __future__ import annotations

from borges.gateway.egress import enforce_egress
from tests.gateway.test_egress import COLUMNS, policy

PROSE = (
    "Rationale: Adjusts for user_id, arm, converted, and revenue to control for drift.\n"
    "Spec: Set ctx['covariates'] = ['user_id', 'arm', 'converted', 'revenue']; keep rows."
)


def test_prose_that_lists_column_names_is_not_a_table() -> None:
    report = enforce_egress([{"role": "user", "content": PROSE}], policy("profile_only"), COLUMNS)
    assert not report.violations


def test_a_markdown_table_with_dataset_headers_is_still_a_violation() -> None:
    table = "| user_id | arm | converted | revenue |\n| 1 | a | 1 | 2.5 |\n| 2 | b | 0 | 1.0 |"
    report = enforce_egress([{"role": "user", "content": table}], policy("profile_only"), COLUMNS)
    assert report.violations


def test_an_indexed_csv_header_is_still_a_table() -> None:
    table = ",user_id,arm,converted,revenue\n0,1,a,1,2.5\n1,2,b,0,1.0"
    report = enforce_egress([{"role": "user", "content": table}], policy("profile_only"), COLUMNS)
    assert report.violations


def test_a_list_of_columns_followed_by_the_same_list_in_code_is_not_a_row() -> None:
    text = (
        "Conventional option(s) at this step: Minimal covariates: user_id, arm, converted\n"
        "Conventional spec: Set ctx['covariates'] = ['user_id', 'arm', 'converted']. Return df."
    )
    report = enforce_egress([{"role": "user", "content": text}], policy("profile_only"), COLUMNS)
    assert not report.violations
