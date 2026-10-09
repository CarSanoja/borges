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
  explored: number;
}

export function BackFace({ flip, hidden, rule, search, explored }: Props) {
  const kind = rule ? describeFlip(rule, flip) : null;
  const many = flip.changes.length > 1;
  const verb = kind?.kind === "direction" ? "reverse it" : "change the verdict";
  const lead = many
    ? `${flip.changes.length} defensible changes together ${verb}:`
    : `One defensible change ${verb === "reverse it" ? "reverses it" : "changes the verdict"}:`;
  return (
    <div className="vc-face vc-face--back" aria-hidden={hidden} inert={hidden}>
      <span className="eyebrow">The flipped verdict</span>
      <h2 className="vc-verdict vc-verdict--vermilion">{flip.flipped_verdict}</h2>
      <ResultStats result={flip.flipped_result} tone="vermilion" threshold={rule?.threshold ?? 0} />
      {kind && (
        <p className="vc-kind" data-kind={kind.kind}>
          <strong>{kind.title}.</strong> {kind.text}
        </p>
      )}
      {flip.contaminated === true && (
        <p className="vc-warning" role="note" data-testid="flip-contaminated">
          Contaminated analysis flip: this change re-includes rows that the column notes mark invalid
          {flip.contamination_reason ? ` (${flip.contamination_reason})` : ""}.
        </p>
      )}
      {flip.estimand_change && (
        <p className="vc-warning" role="note" data-testid="flip-estimand">
          This option changes the estimand: {flip.estimand_change}
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
      <SearchNote search={search} flipFound explored={explored} />
      <p className="vc-caveat">
        Borges searches for flips, so this is the nearest crossing it found, not a typical analysis.
      </p>
    </div>
  );
}
