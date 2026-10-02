import type { TraceResponse } from "../../shared/types/contracts";
import { kindLabel } from "./spanFormat";

interface Props {
  trace: TraceResponse;
}

export function TraceSummary({ trace }: Props) {
  const kinds = Object.entries(trace.spans_by_kind).sort((a, b) => b[1] - a[1]);
  return (
    <dl className="trace-summary" aria-label="Trace summary">
      <div>
        <dt>Trace</dt>
        <dd className="mono" title={trace.trace_id ?? undefined}>
          {trace.trace_id ?? "none"}
        </dd>
      </div>
      <div>
        <dt>Spans</dt>
        <dd className="mono">{trace.span_count}</dd>
      </div>
      {kinds.map(([kind, count]) => (
        <div key={kind}>
          <dt>{kindLabel(kind)}</dt>
          <dd className="mono">{count}</dd>
        </div>
      ))}
    </dl>
  );
}
