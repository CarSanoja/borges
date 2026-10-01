import type { RunSnapshot } from "../../shared/types/contracts";
import { describeRule, modeLabel, statusLabel } from "./runLabels";

interface Props {
  snapshot: RunSnapshot;
  onHome: () => void;
}

export function RunHeader({ snapshot, onHome }: Props) {
  const rule = snapshot.decision_rule;
  const mode = modeLabel(snapshot);
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
        {rule && <span className="chip chip--rule">{describeRule(rule)}</span>}
        <span className={`chip chip--status chip--${snapshot.status}`} role="status">
          <span className="chip__dot" aria-hidden="true" />
          {statusLabel(snapshot)}
        </span>
      </div>
    </header>
  );
}
