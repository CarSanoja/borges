import type { RunSnapshot } from "../../shared/types/contracts";
import { BackFace } from "./BackFace";
import { FrontFace } from "./FrontFace";
import { useTurnOver } from "./useTurnOver";
import { WalkingState } from "./WalkingState";
import { agreementHeadline } from "./agreementHeadline";
import { activeFlip, activeRule, exploredCount, originalVerdict } from "./verdictModel";
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
  const share = agreementHeadline(snapshot);

  if (verdict === null) {
    return (
      <section className="vc" aria-label="Verdict">
        <WalkingState snapshot={snapshot} />
      </section>
    );
  }

  return (
    <section className="vc" aria-label="Verdict" data-state={flip ? (turned ? "flipped" : "found") : "original"}>
      {share && (
        <div className="vc-agree" data-testid="vc-agree" data-inconclusive={share.inconclusive}>
          <p className="vc-agree__line">
            <span className="mono vc-agree__n">{share.agree}</span> of <span className="mono">{share.total}</span> {share.verb}
            {share.suffix}
          </p>
          {share.pLine && <p className="vc-agree__p">{share.pLine}</p>}
        </div>
      )}
      <div className="vc-inner" data-turned={flip !== null && turned}>
        <FrontFace snapshot={snapshot} verdict={verdict} hidden={turned && flip !== null} />
        {flip && <BackFace flip={flip} hidden={!turned} rule={activeRule(snapshot)} search={snapshot.report?.search} explored={exploredCount(snapshot)} />}
      </div>
      {flip && (
        <button type="button" className="vc-toggle" onClick={toggle} aria-pressed={turned}>
          {turned ? "Show the original" : "Show the flip"}
        </button>
      )}
    </section>
  );
}
