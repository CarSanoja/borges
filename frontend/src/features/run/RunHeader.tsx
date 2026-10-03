import type { RunSnapshot } from "../../shared/types/contracts";
import { AppLink, tracePath } from "../../shared/router";
import { ProvenanceChip } from "../cases/ProvenanceChip";
import { describeRule, modeLabel, resumedLabel, statusLabel } from "./runLabels";

interface Props {
  snapshot: RunSnapshot;
  onHome: () => void;
  traceRunId?: string | null;
  provenance?: string | null;
}

export function RunHeader({ snapshot, onHome, traceRunId = null, provenance = null }: Props) {
  const rule = snapshot.decision_rule;
  const mode = modeLabel(snapshot);
  const resumed = resumedLabel(snapshot);
  return (
    <header className="run-header">
      <button type="button" className="run-home" onClick={onHome} aria-label="Back to cases">
        Borges
      </button>
      <div className="run-header__body">
        <h1 className="run-title">{snapshot.title || "Opening the garden"}</h1>
        <p className="run-question">{snapshot.question}</p>
      </div>
      <div className="run-header__meta">
        {mode && <span className="chip chip--mode">{mode}</span>}
        <ProvenanceChip provenance={provenance} />
        {traceRunId && (
          <AppLink to={tracePath(traceRunId)} className="chip chip--link">
            Trace
          </AppLink>
        )}
        {resumed && <span className="chip chip--resumed">{resumed}</span>}
        {rule && <span className="chip chip--rule">{describeRule(rule)}</span>}
        <span className={`chip chip--status chip--${snapshot.status}`} role="status">
          <span className="chip__dot" aria-hidden="true" />
          {statusLabel(snapshot)}
        </span>
      </div>
    </header>
  );
}
