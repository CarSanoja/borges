import type { RunSnapshot } from "../../shared/types/contracts";
import { STAGES, stageState } from "./stageStates";

interface Props {
  snapshot: RunSnapshot;
}

export function StageTimeline({ snapshot }: Props) {
  return (
    <ol className="tm-stages" aria-label="Stages">
      {STAGES.map(({ name, label }) => {
        const state = stageState(snapshot, name);
        const notReexecuted = name === "verifying" && state === "skipped";
        return (
          <li key={name} className="tm-stage" data-state={state}>
            <span className="tm-stage__dot" aria-hidden="true" />
            <span className="tm-stage__label">{notReexecuted ? "Flip not re-executed" : label}</span>
            {!notReexecuted && <span className="visually-hidden"> ({state})</span>}
          </li>
        );
      })}
    </ol>
  );
}
