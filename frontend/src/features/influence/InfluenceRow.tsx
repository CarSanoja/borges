import type { DecisionInfluence } from "../../shared/types/contracts";
import { describeShift, isImmaterialShift } from "./influenceMateriality";

interface Props {
  item: DecisionInfluence;
  scale: number;
  baselineEstimate?: number | null;
}

export function InfluenceRow({ item, scale, baselineEstimate = null }: Props) {
  const share = scale > 0 ? Math.min(1, item.max_abs_delta / scale) : 0;
  const flips = item.flips > 0;
  const context = { largestShift: scale, baselineEstimate, flips: item.flips };
  const immaterial = isImmaterialShift(item.max_abs_delta, context);
  return (
    <li className="ib-row" data-flips={flips} data-material={!immaterial}>
      <span className="ib-title" title={item.title}>
        {item.title}
      </span>
      <span className="ib-track" aria-hidden="true">
        <span className="ib-fill" style={{ width: `${(share * 100).toFixed(1)}%` }} />
      </span>
      <span className={immaterial ? "ib-value ib-value--none" : "ib-value mono"}>
        {describeShift(item.max_abs_delta, context)}
      </span>
      {flips ? (
        <span className="ib-badge">
          {item.flips} {item.flips === 1 ? "flip" : "flips"}
        </span>
      ) : (
        <span className="ib-badge ib-badge--none">holds</span>
      )}
    </li>
  );
}
