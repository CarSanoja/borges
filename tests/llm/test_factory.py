from __future__ import annotations

from pathlib import Path

import pytest

from borges.config import Settings
from borges.llm.client import LLMError
from borges.llm.factory import make_llm
from borges.llm.nebius_provider import NebiusLLM
from borges.llm.scripted_provider import ScriptedLLM


def settings(tmp_path: Path, **kwargs) -> Settings:
    return Settings(_env_file=None, borges_home=tmp_path, **kwargs)


def test_scripted_requires_fixtures(tmp_path: Path) -> None:
    with pytest.raises(LLMError, match="fixtures"):
        make_llm(settings(tmp_path), mode="scripted")


def test_scripted(tmp_path: Path) -> None:
    assert isinstance(make_llm(settings(tmp_path), fixtures_dir=tmp_path), ScriptedLLM)


def test_nebius_requires_key(tmp_path: Path) -> None:
    with pytest.raises(LLMError, match="NEBIUS_API_KEY is not set"):
        make_llm(settings(tmp_path, nebius_api_key=None), mode="nebius")


def test_nebius_wiring(tmp_path: Path) -> None:
    llm = make_llm(
        settings(tmp_path, nebius_api_key="k", borges_spend_cap_usd=2.0),
        mode="nebius",
        run_cap_usd=0.25,
        record_dir=tmp_path / "rec",
    )
    assert isinstance(llm, NebiusLLM)
    assert llm.cache is not None and llm.cache.directory == tmp_path / "llm-cache"
    assert llm.ledger is not None and llm.ledger.cap_usd == 2.0
    assert llm.ledger.path == tmp_path / "spend.json"
    assert llm.run_budget is not None and llm.run_budget.cap_usd == 0.25
    assert llm.record_dir == tmp_path / "rec"


def test_local_wiring_uses_ollama_and_costs_nothing(tmp_path: Path) -> None:
    llm = make_llm(settings(tmp_path), mode="local", record_dir=tmp_path / "rec")
    assert isinstance(llm, NebiusLLM)
    assert str(llm.client.base_url).startswith("http://localhost:11434/v1")
    assert llm.ledger is None and llm.run_budget is None
    assert llm.record_dir == tmp_path / "rec"
    assert llm.cache is not None
    assert {spec.id for spec in llm.role_models.values()} == {"nemotron-3-nano:30b"}
    assert all(spec.cost(1000, 1000) == 0.0 for spec in llm.role_models.values())


def test_local_wiring_honours_settings(tmp_path: Path) -> None:
    llm = make_llm(
        settings(tmp_path, borges_local_base_url="http://h:1/v1", borges_local_model="m:1"),
        mode="local",
    )
    assert str(llm.client.base_url).startswith("http://h:1/v1")
    assert {spec.id for spec in llm.role_models.values()} == {"m:1"}
