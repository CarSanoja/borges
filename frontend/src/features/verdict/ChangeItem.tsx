import type { Change } from "../../shared/types/contracts";
import { DefensibilityMeter } from "./DefensibilityMeter";

interface Props {
  change: Change;
}

export function ChangeItem({ change }: Props) {
  return (
    <li className="vc-change">
      <p className="vc-change__label">{change.to_label}</p>
      <span className="eyebrow vc-change__step">{change.step_title}</span>
      <p className="vc-change__why">{change.rationale}</p>
      {change.source && (
        <span className="vc-change__source">Cited by the model, not checked: {change.source}</span>
      )}
      <DefensibilityMeter value={change.defensibility} />
    </li>
  );
}
