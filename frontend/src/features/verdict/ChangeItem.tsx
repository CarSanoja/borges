import type { Change } from "../../shared/types/contracts";
import { DefensibilityMeter } from "./DefensibilityMeter";

interface Props {
  change: Change;
}

function isLink(source: string): boolean {
  return /^https?:\/\//i.test(source);
}

export function ChangeItem({ change }: Props) {
  return (
    <li className="vc-change">
      <span className="eyebrow">{change.step_title}</span>
      <p className="vc-change__label">{change.to_label}</p>
      <p className="vc-change__why">{change.rationale}</p>
      {change.source &&
        (isLink(change.source) ? (
          <a className="vc-change__source" href={change.source} target="_blank" rel="noreferrer noopener">
            Source
          </a>
        ) : (
          <span className="vc-change__source">Source: {change.source}</span>
        ))}
      <DefensibilityMeter value={change.defensibility} />
    </li>
  );
}
