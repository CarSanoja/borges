from __future__ import annotations

from pathlib import Path

from borges.telemetry.trace_tree import NO_SPANS_REASON, build_trace
from tests.telemetry.conftest import ScriptedRun


def walk(nodes):
    for node in nodes:
        yield node
        yield from walk(node.children)


def test_tree_links_audit_records_by_span_id(scripted_run: ScriptedRun) -> None:
    response = build_trace(scripted_run.run_id, scripted_run.run_dir)
    assert response.reason is None and response.span_count == len(list(walk(response.roots)))
    assert len(response.roots) == 1 and response.roots[0].kind == "run"
    assert response.spans_by_kind["universe"] == 26
    linked = [n for n in walk(response.roots) if n.audit]
    assert {a["kind"] for n in linked for a in n.audit} >= {"model.call", "sandbox.exec"}
    assert all(a["span_id"] == n.span_id for n in linked for a in n.audit)
    assert response.audit_chain is not None and response.audit_chain.ok
    assert response.trace_id


def test_missing_spans_give_an_empty_tree_with_a_reason(tmp_path: Path) -> None:
    response = build_trace("r_old", tmp_path)
    assert response.roots == [] and response.span_count == 0
    assert response.reason == NO_SPANS_REASON
