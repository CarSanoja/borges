from __future__ import annotations

from borges.config import Settings
from borges.fleet.catalog import build_catalog, build_detail


def test_catalog_summarises_the_fleet(settings: Settings) -> None:
    catalog = build_catalog(settings, [])
    assert catalog.summary.total == 12
    assert catalog.summary.by_approval == {"approved": 12}
    assert catalog.summary.blocked == [] and catalog.summary.enforce is False
    judge = next(a for a in catalog.agents if a.agent_id == "judge")
    assert judge.version == "1.0.0" and judge.approval == "approved"


def test_filters(settings: Settings) -> None:
    assert len(build_catalog(settings, [], department="analysis-assurance").agents) == 5
    assert len(build_catalog(settings, [], lifecycle="shadow").agents) == 0
    sandbox = build_catalog(settings, [], capability="sandbox.exec").agents
    assert {a.agent_id for a in sandbox} == {
        "harness",
        "smoke_tester",
        "garden_search",
        "verifier",
    }
    llm = build_catalog(settings, [], capability="llm.invoke").agents
    assert len(llm) == 7


def test_detail_has_descriptor_and_history(settings: Settings) -> None:
    detail = build_detail(settings, "judge")
    assert detail is not None
    assert detail.descriptor.field_sources and detail.versions[0].version == "1.0.0"
    assert build_detail(settings, "ghost") is None
