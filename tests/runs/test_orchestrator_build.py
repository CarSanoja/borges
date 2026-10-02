from __future__ import annotations

from pathlib import Path

from borges.armor.report import ArmorReport
from borges.runs.inputs import resolve_run
from borges.runs.models import RunRequest
from borges.runs.orchestrator_build import build_backend, build_gateway_and_llm
from tests.runs.fakes import make_rig


async def test_gateway_llm_and_backend_are_built_for_the_request(tmp_path: Path) -> None:
    rig = make_rig(tmp_path)
    request = RunRequest(case_id="demo", llm="scripted")
    orchestrator = rig.orchestrator
    resolved = resolve_run(request, orchestrator.registry, orchestrator.settings, None, None)
    gateway, llm = build_gateway_and_llm(orchestrator, "r_1", request, resolved, ArmorReport())
    assert gateway.run_id == "r_1"
    assert rig.factory_calls[0]["fixtures_dir"] == resolved.fixtures_dir
    assert "record_dir" not in rig.factory_calls[0]
    backend = build_backend(orchestrator, request, gateway)
    assert backend is not None


async def test_record_dir_reaches_the_llm_factory(tmp_path: Path) -> None:
    rig = make_rig(tmp_path)
    rig.orchestrator.record_dir = tmp_path / "rec"
    request = RunRequest(case_id="demo", llm="scripted")
    resolved = resolve_run(
        request, rig.orchestrator.registry, rig.orchestrator.settings, None, None
    )
    build_gateway_and_llm(rig.orchestrator, "r_1", request, resolved, ArmorReport())
    assert rig.factory_calls[0]["record_dir"] == tmp_path / "rec"
