import type { Flip } from "../../shared/types/contracts";
import { ChangeItem } from "./ChangeItem";
import { ResultStats } from "./ResultStats";

interface Props {
  flip: Flip;
  hidden: boolean;
}

export function BackFace({ flip, hidden }: Props) {
  const many = flip.changes.length > 1;
  const lead = many
    ? `${flip.changes.length} defensible changes together reverse it:`
    : "One defensible change reverses it:";
  return (
    <div className="vc-face vc-face--back" aria-hidden={hidden} inert={hidden}>
      <span className="eyebrow">The flipped verdict</span>
      <h2 className="vc-verdict vc-verdict--vermilion">{flip.flipped_verdict}</h2>
      <ResultStats result={flip.flipped_result} tone="vermilion" />
      <p className="vc-lead">{lead}</p>
      <ul className={`vc-changes${many ? " vc-changes--many" : ""}`}>
        {flip.changes.map((change) => (
          <ChangeItem key={`${change.step_id}:${change.to_option}`} change={change} />
        ))}
      </ul>
      {flip.reproduced === true && (
        <p className="vc-badge" title={flip.reproduce_command ?? undefined}>
          <svg viewBox="0 0 16 16" aria-hidden="true">
            <path d="M3 8.5 6.5 12 13 4.5" />
          </svg>
          Reproduced from scratch
        </p>
      )}
      {flip.reproduce_command && flip.reproduced !== true && <code className="vc-command">{flip.reproduce_command}</code>}
    </div>
  );
}
