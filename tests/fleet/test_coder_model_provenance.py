from __future__ import annotations

from pathlib import Path

from borges.config import REPO_ROOT, Settings
from borges.fleet.provenance import run_provenance
from borges.llm.client import LIGHTNING, NANO, SUPER
from borges.runs.orchestrator_meta import announced_models


def make(tmp_path: Path, **kwargs) -> Settings:
    return Settings(
        _env_file=None,
        borges_home=tmp_path / "home",
        borges_cases_dir=REPO_ROOT / "cases",
        **kwargs,
    )


def coder_use(settings: Settings, provider: str = "nebius"):
    return next(a for a in run_provenance(settings, provider).agents if a.agent_id == "coder")


def test_default_provenance_records_lightning(tmp_path: Path) -> None:
    use = coder_use(make(tmp_path))
    assert use.model_id == LIGHTNING.id and use.approval == "approved"


def test_nano_run_records_nano_and_a_new_definition(tmp_path: Path) -> None:
    default = coder_use(make(tmp_path))
    use = coder_use(make(tmp_path, borges_coder_model=NANO.id))
    assert use.model_id == NANO.id
    assert use.definition_sha != default.definition_sha
    others = {
        a.agent_id: a.model_id
        for a in run_provenance(make(tmp_path, borges_coder_model=NANO.id), "nebius").agents
    }
    assert others["repairer"] == SUPER.id


def test_announced_models_show_the_chosen_coder(tmp_path: Path) -> None:
    models = announced_models(make(tmp_path, borges_coder_model=NANO.id), "nebius")
    assert models["coder"] == NANO.id and models["repairer"] == SUPER.id
    assert announced_models(make(tmp_path), "nebius")["coder"] == LIGHTNING.id


def test_scripted_runs_ignore_the_choice(tmp_path: Path) -> None:
    assert coder_use(make(tmp_path, borges_coder_model=LIGHTNING.id), "scripted").model_id == (
        "scripted"
    )
