import type { RunSnapshot } from "../../shared/types/contracts";
import { statusLabel } from "../run/runLabels";

interface Props {
  snapshot: RunSnapshot;
}

export function WalkingState({ snapshot }: Props) {
  return (
    <div className="vc-face vc-face--walking">
      <span className="eyebrow">Verdict</span>
      <svg className="vc-threads" viewBox="0 0 120 56" aria-hidden="true">
        <path d="M4 28 H40 C60 28 62 8 84 8 H116" pathLength={1} />
        <path d="M4 28 H116" pathLength={1} />
        <path d="M4 28 H40 C60 28 62 48 84 48 H116" pathLength={1} />
      </svg>
      <h2 className="vc-walking">Walking the garden...</h2>
      <p className="vc-stage" aria-live="polite">
        {statusLabel(snapshot)}
      </p>
    </div>
  );
}
