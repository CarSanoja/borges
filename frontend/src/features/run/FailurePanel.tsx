import type { RunSnapshot } from "../../shared/types/contracts";
import { formatCost } from "../telemetry/telemetryFormat";
import { failureSummary } from "./failureSummary";

interface Props {
  snapshot: RunSnapshot;
}

export function FailurePanel({ snapshot }: Props) {
  const { sentence, suggestion } = failureSummary(snapshot);
  return (
    <section className="run-error run-failure" role="alert" aria-label="Run failed" data-testid="failure-panel">
      <h2 className="run-failure__title">This run could not finish</h2>
      <p>{sentence}</p>
      <p>Nothing was concluded: there is no verdict to trust from this run.</p>
      <p>
        The run cost <span className="mono">{formatCost(snapshot.usage.cost_usd)}</span> before it stopped.
      </p>
      <p>{suggestion}</p>
      <details className="run-failure__details">
        <summary>Technical details</summary>
        <pre className="mono">{snapshot.error}</pre>
      </details>
    </section>
  );
}
