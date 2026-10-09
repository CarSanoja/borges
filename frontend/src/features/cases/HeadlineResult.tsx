import type { CaseCard, ResultBrief } from "../../shared/types/contracts";
import { formatEstimate, formatNumber, formatP } from "../verdict/verdictFormat";
import { ProvenanceChip } from "./ProvenanceChip";
import type { Headline } from "./headline";
import "./headline.css";

interface Props {
  headline: Headline;
  onOpen: (caseId: string) => void;
}

function stats(result: ResultBrief, threshold: number): string {
  return `${formatEstimate(result.estimate, threshold)} [${formatNumber(result.ci_low)}, ${formatNumber(result.ci_high)}], p ${formatP(result.p_value) === "< 0.001" ? "< 0.001" : `= ${formatP(result.p_value)}`}, n = ${result.n.toLocaleString("en-US")}`;
}

export function steadyEstimate(live: NonNullable<CaseCard["live_recording"]>): boolean {
  if (live.flip_kind !== "significance" || !live.baseline || !live.flipped) return false;
  const base = live.baseline.estimate;
  const moved = Math.abs(live.flipped.estimate - base);
  const width = live.flipped.ci_high - live.flipped.ci_low;
  const baseWidth = live.baseline.ci_high - live.baseline.ci_low;
  return moved <= Math.abs(base) * 0.05 && width > baseWidth * 2;
}

function Caveats({ card }: { card: CaseCard }) {
  const live = card.live_recording;
  if (!live) return null;
  return (
    <ul className="headline-caveats">
      {live.contaminated && (
        <li data-testid="headline-contaminated">
          Contaminated analysis flip: it re-includes rows that the column notes mark invalid.
        </li>
      )}
      {steadyEstimate(live) && (
        <li data-testid="headline-steady">
          The point estimate barely moves: this flip comes from a wider interval, not from a different effect.
        </li>
      )}
      {live.estimand_change && <li data-testid="headline-estimand">Changes the estimand: {live.estimand_change}</li>}
      <li>One recorded live run. How often five more live runs found the same verdict and flip is in evidence/repeats.md.</li>
    </ul>
  );
}

function MechanicsDemo({ headline, onOpen }: Props) {
  const { card } = headline;
  return (
    <section className="headline headline--mechanics" aria-label="Demo" data-testid="headline-mechanics">
      <p className="eyebrow">Mechanics demo</p>
      <p className="headline-line">
        <strong>{card.title}</strong> is a scripted offline replay of hand-built fixtures: it shows how the garden works, no model was called and nothing here is a finding.
      </p>
      <ProvenanceChip provenance={card.provenance} />
      <button type="button" className="btn headline-open" onClick={() => onOpen(card.id)}>
        Open the replay
      </button>
    </section>
  );
}

export function HeadlineResult({ headline, onOpen }: Props) {
  if (headline.mechanics) return <MechanicsDemo headline={headline} onOpen={onOpen} />;
  const { card } = headline;
  const live = card.live_recording;
  if (!live || !live.baseline) return null;
  const threshold = card.decision_rule.threshold;
  const flipped = live.flipped_verdict && live.flipped;
  return (
    <section className="headline" aria-label="Headline result" data-testid="headline-result">
      <div className="headline-top">
        <p className="eyebrow">Headline result · {card.title}</p>
        <ProvenanceChip provenance={card.provenance} />
      </div>
      <p className="headline-line">
        The default analysis says <strong>{live.verdict}</strong>:{" "}
        <span className="mono">{stats(live.baseline, threshold)}</span>.
      </p>
      {flipped && live.flipped ? (
        <p className="headline-line">
          {live.flip_changes && live.flip_changes.length > 0 ? `Change ${live.flip_changes.join(" and ")}` : "One defensible change"} and it says{" "}
          <strong className="headline-flip">{live.flipped_verdict}</strong>:{" "}
          <span className="mono">{stats(live.flipped, threshold)}</span>.
        </p>
      ) : (
        <p className="headline-line" data-testid="headline-no-flip">
          {live.universes > 1
            ? `No defensible flip in ${live.universes} universes: the decision held.`
            : "Only the default analysis ran: the decision was not tested."}
        </p>
      )}
      <Caveats card={card} />
      <button type="button" className="btn headline-open" onClick={() => onOpen(card.id)}>
        Open the recorded run
      </button>
    </section>
  );
}
