from __future__ import annotations

import json
from pathlib import Path

from borges.armor.audit import record_decision
from borges.armor.audit_global import global_sink
from borges.armor.report import ArmorDecision
from borges.config import Settings
from borges.telemetry.run_telemetry import global_audit_path


def test_decisions_land_in_the_global_chain_with_the_caller_as_principal(tmp_path: Path) -> None:
    settings = Settings(_env_file=None, borges_home=tmp_path)
    sink = global_sink(settings, "caller://anonymous")
    record_decision(ArmorDecision("refuse", "injection", "question", "override"), sink, stage="x")
    records = [json.loads(line) for line in global_audit_path(settings).read_text().splitlines()]
    last = records[-1]
    assert last["kind"] == "armor.screen" and last["decision"] == "deny"
    assert last["principal"] == "caller://anonymous"
    assert last["data"]["action"] == "refuse" and last["data"]["stage"] == "x"
