import type { Report } from "../../shared/types/contracts";
import { formatPercent } from "./verdictFormat";

interface Props {
  report: Report;
}

export function Robustness({ report }: Props) {
  const agree = Math.max(0, report.n_universes - report.n_flipped);
  return (
    <div className="vc-robust">
      <div className="vc-robust__head">
        <span className="eyebrow">Robustness</span>
        <span className="mono vc-robust__value">{formatPercent(report.robustness)}</span>
      </div>
      <span className="vc-robust__track" aria-hidden="true">
        <span className="vc-robust__fill" style={{ width: formatPercent(report.robustness) }} />
      </span>
      <p className="vc-robust__note">
        {agree} of {report.n_universes} explored universes agree
      </p>
    </div>
  );
}
