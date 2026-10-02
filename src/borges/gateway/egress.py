from __future__ import annotations

import json
from dataclasses import dataclass, field

from borges.gateway.egress_redact import redact_value
from borges.gateway.egress_scan import (
    SampleSpan,
    delimited_dump_size,
    find_sample_rows,
    has_profile,
    record_dump_sizes,
)
from borges.gateway.policy_models import EGRESS_RANK, AgentPolicy


@dataclass
class EgressReport:
    messages: list[dict[str, str]]
    rows_stripped: int = 0
    rows_redacted: int = 0
    violations: list[str] = field(default_factory=list)

    @property
    def changed(self) -> bool:
        return bool(self.rows_stripped or self.rows_redacted)


def _compact(value: object) -> str:
    return json.dumps(value, separators=(",", ":"), ensure_ascii=False)


def _rewrite(
    content: str, spans: list[SampleSpan], agent: AgentPolicy, report: EgressReport
) -> str:
    allowed = agent.max_sample_rows if agent.egress == "sample_rows" else 0
    out, cursor = [], 0
    for span in spans:
        original = span.rows[:allowed]
        kept = [redact_value(row) for row in original]
        report.rows_stripped += len(span.rows) - len(original)
        report.rows_redacted += sum(1 for a, b in zip(kept, original, strict=True) if a != b)
        if kept == span.rows:
            continue
        out.append(content[cursor : span.start])
        out.append(_compact(kept))
        cursor = span.end
    out.append(content[cursor:])
    return "".join(out)


def _violations(
    content: str, spans: list[SampleSpan], agent: AgentPolicy, columns: frozenset[str]
) -> list[str]:
    found: list[str] = []
    rank = EGRESS_RANK[agent.egress]
    row_limit = agent.max_sample_rows if agent.egress == "sample_rows" else 0
    for size in [
        *record_dump_sizes(content, spans, columns),
        delimited_dump_size(content, columns),
    ]:
        if size > row_limit:
            found.append(
                f"{size} raw data rows in a message exceed the {agent.egress!r} egress class"
            )
    if rank == 0 and has_profile(content):
        found.append("dataset profile content exceeds the 'none' egress class")
    return found


def enforce_egress(
    messages: list[dict[str, str]], agent: AgentPolicy, columns: frozenset[str] = frozenset()
) -> EgressReport:
    report = EgressReport(messages=[])
    for message in messages:
        content = message.get("content", "")
        spans = find_sample_rows(content)
        report.violations.extend(_violations(content, spans, agent, columns))
        if spans:
            content = _rewrite(content, spans, agent, report)
        report.messages.append(
            message if content == message.get("content") else {**message, "content": content}
        )
    return report
