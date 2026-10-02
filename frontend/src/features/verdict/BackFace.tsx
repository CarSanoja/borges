import type { DecisionRule, Flip, SearchSummary } from "../../shared/types/contracts";
import { ChangeItem } from "./ChangeItem";
import { describeFlip } from "./flipKind";
import { ResultStats } from "./ResultStats";
import { SearchNote } from "./SearchNote";

interface Props {
  flip: Flip;
  hidden: boolean;
  rule: DecisionRule | null;
  search?: SearchSummary | null;
}

export function BackFace({ flip, hidden, rule, search }: Props) {
  const kind = rule ? describeFlip(rule, flip) : null;
  const many = flip.changes.length > 1;
  const lead = many
    ? `${flip.changes.length} defensible changes together reverse it:`
    : "One defensible change reverses it:";
  return (
    <div className="vc-face vc-face--back" aria-hidden={hidden} inert={hidden}>
      <span className="eyebrow">The flipped verdict</span>
      <h2 className="vc-verdict vc-verdict--vermilion">{flip.flipped_verdict}</h2>
      <ResultStats result={flip.flipped_result} tone="vermilion" />
      {kind && (
        <p className="vc-kind" data-kind={kind.kind}>
          <strong>{kind.title}.</strong> {kind.text}
        </p>
      )}
      <p className="vc-lead">{lead}</p>
      <ul className={`vc-changes${many ? " vc-changes--many" : ""}`}>
        {flip.changes.map((change) => (
          <ChangeItem key={`${change.step_id}:${change.to_option}`} change={change} />
        ))}
      </ul>
      {flip.reproduced === true && (
        <p className="vc-badge">
          <svg viewBox="0 0 16 16" aria-hidden="true">
            <path d="M3 8.5 6.5 12 13 4.5" />
          </svg>
          Reproduced from scratch
        </p>
      )}
      {flip.reproduced === false && (
        <p className="vc-warning" role="note">
          Not reproduced on a fresh re-execution: treat as unconfirmed
        </p>
      )}
      <SearchNote search={search} flipFound />
      <p className="vc-caveat">
        Borges searches for flips, so this is the nearest crossing it found, not a typical analysis.
      </p>
    </div>
  );
}
