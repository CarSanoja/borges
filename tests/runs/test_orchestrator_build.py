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


async def test_memory_is_built_for_the_runs_principal_and_only_when_enabled(
    tmp_path: Path,
) -> None:
    from borges.runs.orchestrator_build import build_memory

    rig = make_rig(tmp_path)
    orchestrator = rig.orchestrator
    request = RunRequest(case_id="demo", llm="scripted")
    resolved = resolve_run(request, orchestrator.registry, orchestrator.settings, None, None)
    orchestrator.register("r_1", request, resolved, extra={"principal": "caller://acme"})
    args = (orchestrator, "r_1", request, resolved, None, ArmorReport(), False)
    assert build_memory(*args) is None

    orchestrator.settings = orchestrator.settings.model_copy(
        update={"borges_memory": True, "borges_memory_key": "k" * 32}
    )
    memory = build_memory(*args)
    assert memory is not None and memory.session.tenant == "acme" and memory.session.reads

    resumed = build_memory(orchestrator, "r_1", request, resolved, None, ArmorReport(), True)
    assert resumed is not None and resumed.session.reads is False

    edited = RunRequest(case_id="demo", llm="scripted", question="my own question")
    orchestrator.register("r_2", edited, resolved, extra={"principal": "caller://acme"})
    keyed = build_memory(orchestrator, "r_2", edited, resolved, None, ArmorReport(), False)
    assert keyed is not None and keyed.session.tenant == "acme"

    orchestrator.register("r_3", edited, resolved)
    assert build_memory(orchestrator, "r_3", edited, resolved, None, ArmorReport(), False) is None
