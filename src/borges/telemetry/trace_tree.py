from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from borges.telemetry.audit_crosscheck import verify_run_chain
from borges.telemetry.audit_verify import ChainReport, read_records

NO_SPANS_REASON = (
    "This run has no spans: it was recorded before tracing existed or tracing was unavailable."
)


class SpanNode(BaseModel):
    span_id: str
    parent_span_id: str | None
    name: str
    kind: str | None
    status: str
    start_ns: int
    end_ns: int | None
    duration_ms: float | None
    attributes: dict[str, Any] = Field(default_factory=dict)
    audit: list[dict[str, Any]] = Field(default_factory=list)
    children: list[SpanNode] = Field(default_factory=list)


class TraceResponse(BaseModel):
    run_id: str
    trace_id: str | None = None
    span_count: int = 0
    spans_by_kind: dict[str, int] = Field(default_factory=dict)
    roots: list[SpanNode] = Field(default_factory=list)
    unlinked_audit: list[dict[str, Any]] = Field(default_factory=list)
    audit_chain: ChainReport | None = None
    reason: str | None = None


def read_spans(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    spans = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        try:
            spans.append(json.loads(raw))
        except ValueError:
            continue
    return spans


def _node(raw: dict[str, Any]) -> SpanNode:
    start, end = raw.get("start_ns") or 0, raw.get("end_ns")
    return SpanNode(
        span_id=raw["span_id"],
        parent_span_id=raw.get("parent_span_id"),
        name=raw.get("name", ""),
        kind=raw.get("kind"),
        status=raw.get("status", "UNSET"),
        start_ns=start,
        end_ns=end,
        duration_ms=round((end - start) / 1e6, 3) if end else None,
        attributes=raw.get("attributes", {}),
    )


def build_trace(run_id: str, run_dir: Path, global_path: Path | None = None) -> TraceResponse:
    spans = read_spans(run_dir / "spans.jsonl")
    if not spans:
        return TraceResponse(run_id=run_id, reason=NO_SPANS_REASON)
    nodes = {raw["span_id"]: _node(raw) for raw in spans}
    records = read_records(run_dir / "audit.jsonl")
    unlinked: list[dict[str, Any]] = []
    for record in records:
        dump = record.model_dump(mode="json")
        target = nodes.get(record.span_id or "")
        (target.audit if target else unlinked).append(dump)
    children: dict[str | None, list[SpanNode]] = defaultdict(list)
    for node in nodes.values():
        parent = node.parent_span_id if node.parent_span_id in nodes else None
        children[parent].append(node)
    for node in nodes.values():
        node.children = sorted(children.get(node.span_id, []), key=lambda n: n.start_ns)
    kinds: dict[str, int] = defaultdict(int)
    for node in nodes.values():
        kinds[node.kind or "unknown"] += 1
    return TraceResponse(
        run_id=run_id,
        trace_id=spans[0].get("trace_id"),
        span_count=len(nodes),
        spans_by_kind=dict(kinds),
        roots=sorted(children.get(None, []), key=lambda n: n.start_ns),
        unlinked_audit=unlinked,
        audit_chain=verify_run_chain(run_dir / "audit.jsonl", global_path, run_id).model_copy(
            update={"path": f"{run_id}/audit.jsonl"}
        ),
    )
