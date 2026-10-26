import { useMemo } from "react";
import type { RunSnapshot } from "../../shared/types/contracts";
import { computeInfluences, rankInfluences } from "./computeInfluences";
import { InfluenceRow } from "./InfluenceRow";
import "./influence.css";

interface Props {
  snapshot: RunSnapshot;
}

export function InfluenceBars({ snapshot }: Props) {
  const reported = snapshot.report?.influences;
  const items = useMemo(
    () => rankInfluences(reported && reported.length > 0 ? reported : computeInfluences(snapshot)),
    [reported, snapshot],
  );
  const scale = items.reduce((max, item) => Math.max(max, item.max_abs_delta), 0);
  const baselineEstimate = snapshot.report?.original_result.estimate ?? null;
  const metric = snapshot.decision_rule?.metric;

  return (
    <section className="panel ib" aria-label="Decision influence">
      <header className="ib-head">
        <span className="eyebrow">Decision influence</span>
        <span className="ib-unit">{metric ? `largest move of the estimate, in ${metric}` : "largest move of the estimate"}</span>
      </header>
      {items.length === 0 ? (
        <p className="ib-empty">Influence appears as the first forks finish.</p>
      ) : (
        <ol className="ib-list">
          {items.map((item) => (
            <InfluenceRow key={item.step_id} item={item} scale={scale} baselineEstimate={baselineEstimate} />
          ))}
        </ol>
      )}
    </section>
  );
}
