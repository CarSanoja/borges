from __future__ import annotations

import json

from borges.gateway.egress import enforce_egress
from borges.gateway.policy_models import AgentPolicy

COLUMNS = frozenset({"user_id", "arm", "converted", "revenue"})


def policy(egress: str, rows: int = 0) -> AgentPolicy:
    return AgentPolicy(
        models=["m"],
        max_tokens=100,
        max_calls_per_run=1,
        max_cost_usd_per_run=1,
        max_concurrent_calls=1,
        egress=egress,
        max_sample_rows=rows,
    )


def rows(n: int) -> list[dict]:
    return [
        {"user_id": 1000 + i, "arm": "a", "converted": i % 2, "revenue": float(i)} for i in range(n)
    ]


def profile_message(sample: list[dict]) -> list[dict[str, str]]:
    body = {"name": "d", "n_rows": 99, "columns": [{"name": "arm", "n_missing": 0, "n_unique": 2}]}
    body["sample_rows"] = sample
    text = "Dataset profile: " + json.dumps(body, separators=(",", ":"))
    return [{"role": "system", "content": "s"}, {"role": "user", "content": text}]


def test_rows_within_the_class_pass_untouched() -> None:
    messages = profile_message(rows(3))
    report = enforce_egress(messages, policy("sample_rows", 5))
    assert report.messages == messages and not report.changed and not report.violations


def test_profile_only_strips_the_sample_rows() -> None:
    report = enforce_egress(profile_message(rows(5)), policy("profile_only"))
    content = report.messages[1]["content"]
    assert '"sample_rows":[]' in content and "1000" not in content
    assert report.rows_stripped == 5 and report.changed and not report.violations
    assert '"n_unique":2' in content


def test_sample_rows_class_truncates_to_its_bound() -> None:
    report = enforce_egress(profile_message(rows(5)), policy("sample_rows", 2))
    sent = json.loads(report.messages[1]["content"].split("Dataset profile: ")[1])
    assert len(sent["sample_rows"]) == 2 and report.rows_stripped == 3


def test_sample_rows_are_redacted_for_emails_and_long_numbers() -> None:
    sample = [{"user_id": 1, "contact": "ana@example.org", "card": "4111111111111111"}]
    report = enforce_egress(profile_message(sample), policy("sample_rows", 5))
    content = report.messages[1]["content"]
    assert "ana@example.org" not in content and "4111111111111111" not in content
    assert content.count("[redacted]") == 2 and report.rows_redacted == 1


def test_none_class_rejects_profile_content() -> None:
    report = enforce_egress(profile_message([]), policy("none"))
    assert any("'none' egress class" in v for v in report.violations)


def test_raw_record_dump_above_the_class_is_a_violation() -> None:
    dump = "Here is the data:\n" + json.dumps(rows(8))
    report = enforce_egress([{"role": "user", "content": dump}], policy("profile_only"), COLUMNS)
    assert report.violations and "8 raw data rows" in report.violations[0]


def test_record_dump_up_to_the_bound_is_allowed() -> None:
    dump = json.dumps(rows(6))
    ok = enforce_egress([{"role": "user", "content": dump}], policy("sample_rows", 6), COLUMNS)
    assert not ok.violations
    bad = enforce_egress([{"role": "user", "content": dump}], policy("sample_rows", 5), COLUMNS)
    assert bad.violations


def test_delimited_table_with_dataset_headers_is_a_violation() -> None:
    table = "user_id,arm,converted,revenue\n" + "\n".join(f"{i},a,1,2.5" for i in range(9))
    report = enforce_egress([{"role": "user", "content": table}], policy("profile_only"), COLUMNS)
    assert report.violations and "9 raw data rows" in report.violations[0]


def test_records_that_are_not_dataset_rows_are_not_flagged() -> None:
    table = [{"step": f"s{i}", "n_before": i, "n_after": i - 1} for i in range(10)]
    content = json.dumps(table)
    report = enforce_egress([{"role": "user", "content": content}], policy("profile_only"), COLUMNS)
    assert not report.violations


def test_without_known_columns_structural_detection_is_off() -> None:
    report = enforce_egress([{"role": "user", "content": json.dumps(rows(9))}], policy("none"))
    assert not report.violations


def test_original_messages_are_not_mutated() -> None:
    messages = profile_message(rows(5))
    before = json.dumps(messages)
    enforce_egress(messages, policy("profile_only"))
    assert json.dumps(messages) == before
