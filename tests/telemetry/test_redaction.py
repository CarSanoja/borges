from __future__ import annotations

from typing import Any

import pytest

from borges.telemetry import event_audit
from borges.telemetry.redaction import redact_text


def test_paths_and_key_like_tokens_are_removed() -> None:
    text = (
        "FileNotFoundError: /Users/cs/vault/.env used nvapi-abcdef1234567890XYZ and "
        "Bearer abcdef1234567890 plus " + "a" * 48
    )
    out = redact_text(text)
    for leaked in ("/Users", "vault", "nvapi-abcdef", "abcdef1234567890", "a" * 40):
        assert leaked not in out


def test_ordinary_text_is_kept() -> None:
    assert redact_text("budget exceeded for run") == "budget exceeded for run"


def test_the_limit_applies_after_redaction() -> None:
    assert len(redact_text("ab " * 200, 300)) == 300


def test_failure_and_verdict_reasons_pass_through_redaction(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen: list[dict[str, Any]] = []
    monkeypatch.setattr(event_audit.hooks, "audit", lambda kind, **kw: seen.append(kw))
    event_audit.audit_run_event(
        "run.failed", {"error": "OSError: /Users/cs/x/.env nvapi-1234567890abcd"}
    )
    event_audit.audit_run_event("option.judged", {"reason": "see /private/tmp/secret.csv"})
    reasons = " ".join(str(item["reason"]) for item in seen)
    assert "/Users" not in reasons and "nvapi-" not in reasons and "/private" not in reasons


def test_personal_data_is_redacted_from_audit_text() -> None:
    out = redact_text("failed for maria@example.com at 192.168.1.10")
    assert out == "failed for [redacted:email] at [redacted:ip_address]"
