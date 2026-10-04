from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from borges.config import Settings
from borges.llm.client import (
    DEFAULT_ROLE_MODELS,
    KNOWN_MODELS,
    LIGHTNING,
    NANO,
    SUPER,
    LLMError,
    Role,
)
from borges.llm.coder_model import nebius_role_models
from borges.llm.factory import make_llm
from borges.llm.nebius_provider import NebiusLLM


def settings(tmp_path: Path, **kwargs) -> Settings:
    return Settings(_env_file=None, borges_home=tmp_path, nebius_api_key="k", **kwargs)


def test_lightning_is_known_with_the_nano_price() -> None:
    assert KNOWN_MODELS[LIGHTNING.id] is LIGHTNING
    assert (LIGHTNING.input_usd_per_m, LIGHTNING.output_usd_per_m) == (0.06, 0.24)


def test_default_is_lightning_and_blank_means_default(monkeypatch: pytest.MonkeyPatch) -> None:
    assert Settings(_env_file=None).borges_coder_model == LIGHTNING.id
    monkeypatch.setenv("BORGES_CODER_MODEL", "")
    assert Settings(_env_file=None).borges_coder_model == LIGHTNING.id


def test_env_selects_an_allowed_model(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BORGES_CODER_MODEL", LIGHTNING.id)
    assert Settings(_env_file=None).borges_coder_model == LIGHTNING.id


@pytest.mark.parametrize("bad", ["gpt-5", "nvidia/Nemotron-3-Ultra-550b-a55b", "nano"])
def test_unknown_or_non_allowed_value_fails_fast(bad: str) -> None:
    with pytest.raises(ValidationError, match="not an allowed coder model"):
        Settings(_env_file=None, borges_coder_model=bad)


def test_default_role_map_is_unchanged(tmp_path: Path) -> None:
    llm = make_llm(settings(tmp_path), mode="nebius")
    assert isinstance(llm, NebiusLLM) and llm.role_models == DEFAULT_ROLE_MODELS


def test_factory_swaps_only_the_coder(tmp_path: Path) -> None:
    llm = make_llm(settings(tmp_path, borges_coder_model=LIGHTNING.id), mode="nebius")
    assert isinstance(llm, NebiusLLM)
    assert llm.role_models[Role.CODER] is LIGHTNING
    assert llm.role_models[Role.REPAIRER] is SUPER
    for role, spec in DEFAULT_ROLE_MODELS.items():
        if role is not Role.CODER:
            assert llm.role_models[role] is spec


def test_super_is_selectable_for_the_coder() -> None:
    assert nebius_role_models(SUPER.id)[Role.CODER] is SUPER


def test_policy_that_does_not_list_the_choice_is_refused(tmp_path: Path) -> None:
    policy = tmp_path / "gateway.json"
    from borges.config import REPO_ROOT

    text = (REPO_ROOT / "policy" / "gateway.json").read_text()
    policy.write_text(text.replace('"nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B", ', ""))
    chosen = settings(tmp_path, borges_coder_model=NANO.id, borges_gateway_policy=policy)
    with pytest.raises(LLMError, match="not allowed for the coder"):
        make_llm(chosen, mode="nebius")
