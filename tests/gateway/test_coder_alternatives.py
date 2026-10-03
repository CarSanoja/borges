from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from borges.config import REPO_ROOT, Settings
from borges.gateway.errors import GatewayDenied
from borges.gateway.llm_models import build_chain
from borges.gateway.policy_load import policy_for
from borges.gateway.policy_models import AgentPolicy
from borges.llm.client import LIGHTNING, NANO, SUPER, ULTRA, Role

from .conftest import FakeLLM
from .test_llm_route import Status, ask

BASE = dict(
    max_tokens=10,
    max_calls_per_run=1,
    max_cost_usd_per_run=0.1,
    max_concurrent_calls=1,
    egress="profile_only",
)


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(
        _env_file=None,
        borges_home=tmp_path / "home",
        borges_runs_dir=tmp_path / "runs",
        borges_cases_dir=REPO_ROOT / "cases",
        borges_coder_model=LIGHTNING.id,
    )


def test_alternatives_are_not_fallbacks() -> None:
    agent = AgentPolicy(models=["a"], alternatives=["b"], **BASE)
    assert agent.fallbacks == [] and agent.allowed == ["a", "b"]
    assert build_chain(agent, "b", None).models == ["b"]
    assert build_chain(agent, "a", None).models == ["a"]


def test_alternatives_cannot_repeat_models() -> None:
    with pytest.raises(ValidationError, match="repeats"):
        AgentPolicy(models=["a"], alternatives=["a"], **BASE)
    with pytest.raises(ValidationError, match="twice"):
        AgentPolicy(models=["a"], alternatives=["b", "b"], **BASE)


def test_tracked_policy_lists_lightning_without_changing_the_chain(settings: Settings) -> None:
    coder = policy_for(settings).agent("coder")
    assert coder.models == [NANO.id] and coder.fallbacks == []
    assert LIGHTNING.id in coder.alternatives and SUPER.id in coder.alternatives


async def test_chosen_model_is_allowed_with_its_capability(make_gateway) -> None:
    llm = FakeLLM(role_models={Role.CODER: LIGHTNING})
    routed = await ask(make_gateway(), llm, Role.CODER)
    assert routed.model == LIGHTNING.id and not routed.fallback
    assert llm.calls[0]["model"] == LIGHTNING.id


async def test_alternative_never_falls_back_to_another(make_gateway) -> None:
    llm = FakeLLM([Status(503)] * 3, role_models={Role.CODER: LIGHTNING})
    with pytest.raises(Status):
        await ask(make_gateway(), llm, Role.CODER)
    assert {c["model"] for c in llm.calls} == {LIGHTNING.id}


async def test_other_models_are_still_denied(make_gateway) -> None:
    llm = FakeLLM(role_models={Role.CODER: ULTRA})
    with pytest.raises(GatewayDenied, match="not allowed for coder"):
        await ask(make_gateway(), llm, Role.CODER)
    assert not llm.calls


async def test_nano_is_denied_by_capability_when_lightning_is_chosen(make_gateway) -> None:
    llm = FakeLLM(role_models={Role.CODER: NANO})
    with pytest.raises(GatewayDenied) as caught:
        await ask(make_gateway(), llm, Role.CODER)
    assert caught.value.rule == "capability" and not llm.calls
