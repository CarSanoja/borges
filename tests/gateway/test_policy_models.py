from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from borges.config import REPO_ROOT
from borges.fleet.roster import ROSTER
from borges.gateway.policy_models import AgentPolicy, GatewayPolicy
from borges.llm.client import DEFAULT_ROLE_MODELS

POLICY_FILE = REPO_ROOT / "policy" / "gateway.json"


def agent(**changes: object) -> dict:
    base = {
        "models": ["m1"],
        "max_tokens": 10,
        "max_calls_per_run": 1,
        "max_cost_usd_per_run": 0.1,
        "max_concurrent_calls": 1,
        "egress": "profile_only",
    }
    return {**base, **changes}


def test_agent_policy_exposes_primary_and_fallbacks() -> None:
    policy = AgentPolicy(**agent(models=["a", "b", "c"]))
    assert policy.primary == "a" and policy.fallbacks == ["b", "c"]


def test_duplicate_models_are_rejected() -> None:
    with pytest.raises(ValidationError, match="twice"):
        AgentPolicy(**agent(models=["a", "a"]))


def test_empty_model_chain_is_rejected() -> None:
    with pytest.raises(ValidationError):
        AgentPolicy(**agent(models=[]))


def test_sample_rows_need_a_positive_bound() -> None:
    with pytest.raises(ValidationError, match="max_sample_rows"):
        AgentPolicy(**agent(egress="sample_rows"))
    assert AgentPolicy(**agent(egress="sample_rows", max_sample_rows=3)).max_sample_rows == 3


def test_a_row_bound_without_the_class_is_rejected() -> None:
    with pytest.raises(ValidationError, match="sample_rows"):
        AgentPolicy(**agent(max_sample_rows=2))


def test_unknown_egress_class_is_rejected() -> None:
    with pytest.raises(ValidationError):
        AgentPolicy(**agent(egress="everything"))


def test_unknown_keys_are_rejected() -> None:
    with pytest.raises(ValidationError):
        AgentPolicy(**agent(surprise=1))


def test_sandbox_network_can_only_be_none() -> None:
    data = json.loads(POLICY_FILE.read_text())
    data["sandbox"]["network"] = "open"
    with pytest.raises(ValidationError):
        GatewayPolicy.model_validate(data)


def test_retry_delay_ceiling_cannot_be_below_the_base() -> None:
    data = json.loads(POLICY_FILE.read_text())
    data["retry"]["max_delay_s"] = 0.1
    with pytest.raises(ValidationError, match="max_delay_s"):
        GatewayPolicy.model_validate(data)


def test_tracked_policy_validates() -> None:
    GatewayPolicy.model_validate_json(POLICY_FILE.read_text())


def test_tracked_policy_covers_every_llm_agent_with_its_primary_model() -> None:
    policy = GatewayPolicy.model_validate_json(POLICY_FILE.read_text())
    for declaration in ROSTER:
        if declaration.llm_role is None:
            assert declaration.agent_id not in policy.agents
            continue
        assert (
            policy.agents[declaration.agent_id].primary
            == DEFAULT_ROLE_MODELS[declaration.llm_role].id
        )


def test_tracked_sandbox_policy_matches_the_harness_constants() -> None:
    from borges.analysis import harness

    policy = GatewayPolicy.model_validate_json(POLICY_FILE.read_text())
    assert policy.sandbox.step_dir == harness.STEPS_DIR
    assert policy.sandbox.data_file == harness.DATA_FILE
    assert policy.sandbox.executor == "harness"
    assert policy.sandbox.network == "none"


def test_policy_file_is_tracked_not_ignored() -> None:
    assert Path(POLICY_FILE).is_file()
