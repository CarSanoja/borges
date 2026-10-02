from __future__ import annotations

from borges.config import Settings
from borges.gateway.armor_hooks import ArmorContext, NoopArmor
from borges.gateway.core import build_gateway
from borges.gateway.errors import GatewayDenied
from borges.identity.run_identity import mint_run_identity
from borges.llm.client import LLMResponse, Role, Usage
from borges.telemetry.audit_verify import read_records
from borges.telemetry.run_telemetry import global_audit_path


def test_denial_is_an_audit_record_with_principal_and_policy_sha(make_gateway, audit) -> None:
    gateway = make_gateway()
    error = gateway.deny("egress", "too many rows", "judge", key="k")
    assert isinstance(error, GatewayDenied) and error.audited
    record = audit.denials()[0]
    assert record["decision"] == "deny" and record["reason"] == "too many rows"
    assert record["principal"] == "agent://borges/judge"
    assert record["policy_sha"] == gateway.policy_sha and record["key"] == "k"


def test_noop_armor_is_identity() -> None:
    context = ArmorContext("r", "planner", "agent://borges/planner", "m", "k")
    messages = [{"role": "user", "content": "x"}]
    response = LLMResponse(role=Role.PLANNER, text="t", usage=Usage(model="m"))
    armor = NoopArmor()
    assert armor.screen_input(context, messages) is messages
    assert armor.screen_output(context, response) is response


def test_build_gateway_denials_reach_the_global_audit_outside_a_run(tmp_path) -> None:
    settings = Settings(_env_file=None, borges_home=tmp_path / "home")
    gateway = build_gateway(settings, "r_x", mint_run_identity(settings, "r_x"))
    gateway.deny("model", "not allowed", "coder")
    records = read_records(global_audit_path(settings))
    assert any(r.kind == "gateway.deny" and r.decision == "deny" for r in records)


def test_build_gateway_carries_local_model_and_columns(tmp_path) -> None:
    settings = Settings(_env_file=None, borges_home=tmp_path / "home")
    gateway = build_gateway(settings, "r", None, "local", dataset_columns=frozenset({"a"}))
    assert gateway.local_model == settings.borges_local_model
    assert gateway.dataset_columns == {"a"}
    assert build_gateway(settings, "r", None, "scripted").local_model is None
