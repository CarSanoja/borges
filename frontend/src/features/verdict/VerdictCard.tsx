import type { RunSnapshot } from "../../shared/types/contracts";
import { BackFace } from "./BackFace";
import { FrontFace } from "./FrontFace";
import { useTurnOver } from "./useTurnOver";
import { WalkingState } from "./WalkingState";
import { activeFlip, activeRule, originalVerdict } from "./verdictModel";
import "./verdict.css";
import "./verdictBack.css";
import "./verdictWalking.css";

interface Props {
  snapshot: RunSnapshot;
}

export function VerdictCard({ snapshot }: Props) {
  const verdict = originalVerdict(snapshot);
  const flip = activeFlip(snapshot);
  const [turned, toggle] = useTurnOver(flip !== null);

  if (verdict === null) {
    return (
      <section className="vc" aria-label="Verdict">
        <WalkingState snapshot={snapshot} />
      </section>
    );
  }

  return (
    <section className="vc" aria-label="Verdict" data-state={flip ? (turned ? "flipped" : "found") : "original"}>
      <div className="vc-inner" data-turned={flip !== null && turned}>
        <FrontFace snapshot={snapshot} verdict={verdict} hidden={turned && flip !== null} />
        {flip && <BackFace flip={flip} hidden={!turned} rule={activeRule(snapshot)} />}
      </div>
      {flip && (
        <button type="button" className="vc-toggle" onClick={toggle} aria-pressed={turned}>
          {turned ? "Show the original" : "Show the flip"}
        </button>
      )}
    </section>
  );
}
