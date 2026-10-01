import type { DecisionInfluence } from "../../shared/types/contracts";
import { formatNumber } from "../verdict/verdictFormat";

interface Props {
  item: DecisionInfluence;
  scale: number;
}

export function InfluenceRow({ item, scale }: Props) {
  const share = scale > 0 ? Math.min(1, item.max_abs_delta / scale) : 0;
  const flips = item.flips > 0;
  return (
    <li className="ib-row" data-flips={flips}>
      <span className="ib-title">{item.title}</span>
      <span className="ib-track" aria-hidden="true">
        <span className="ib-fill" style={{ width: `${(share * 100).toFixed(1)}%` }} />
      </span>
      <span className="ib-value mono">{formatNumber(item.max_abs_delta)}</span>
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
