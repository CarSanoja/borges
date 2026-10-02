from __future__ import annotations

from pathlib import Path

import pytest
from fastapi import HTTPException

from borges.config import Settings
from borges.telemetry.audit_verify import read_records, verify_chain
from borges.telemetry.policy_audit import audited_policy
from borges.telemetry.run_telemetry import global_audit_path


def settings(tmp_path: Path) -> Settings:
    return Settings(_env_file=None, borges_home=tmp_path)


def test_accept_and_deny_land_in_the_global_chain(tmp_path: Path) -> None:
    def check(value: int) -> int:
        if value < 0:
            raise HTTPException(status_code=429, detail="Borges is busy")
        return value * 2

    assert audited_policy(settings(tmp_path), "run", check, 2, case_id="c") == 4
    with pytest.raises(HTTPException):
        audited_policy(settings(tmp_path), "run", check, -1, case_id="c")
    path = global_audit_path(settings(tmp_path))
    allow, deny = read_records(path)
    assert (allow.kind, allow.decision, allow.data) == ("policy.run", "allow", {"case_id": "c"})
    assert deny.decision == "deny" and deny.reason == "Borges is busy"
    assert deny.data == {"status": 429, "case_id": "c"}
    assert verify_chain(path).ok
