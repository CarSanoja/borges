import { useState } from "react";
import { createRun } from "../../shared/api/client";
import type { CaseCard } from "../../shared/types/contracts";
import { formatCost, stampStatement } from "../recording/recordingText";
import "../recording/recording.css";
import { describeRule } from "./decisionRuleText";
import { ProvenanceChip } from "./ProvenanceChip";

interface Props {
  card: CaseCard;
  liveAvailable: boolean;
  onOpenRun: (runId: string) => void;
  onOpenReplay: (caseId: string) => void;
}

export function CaseCardView({ card, liveAvailable, onOpenRun, onOpenReplay }: Props) {
  const liveOnly = card.live_only === true;
  const [busy, setBusy] = useState<"scripted" | "nebius" | null>(null);
  const [error, setError] = useState<string | null>(null);

  const start = async (llm: "scripted" | "nebius") => {
    setBusy(llm);
    setError(null);
    try {
      const run = await createRun({ case_id: card.id, llm });
      onOpenRun(run.run_id);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Could not start the run");
      setBusy(null);
    }
  };

  return (
    <article className="case-card">
      <div className="case-tags">
        <ProvenanceChip provenance={card.provenance} />
      </div>
      <p className="eyebrow">{card.subtitle}</p>
      {card.live_recording && (
        <p className="recording-badge" data-testid="live-badge">
          Live run recorded · est. ${formatCost(card.live_recording.cost_usd)}
        </p>
      )}
      {card.live_recording && card.recording_meta?.live && (
        <p className="recording-stamp" data-testid="live-stamp">
          {stampStatement(card.recording_meta.live)}
        </p>
      )}
      {liveOnly && !card.live_recording && <p className="case-live-only">Needs live mode: runs only with a Nemotron key</p>}
      <h3 className="case-title">{card.title}</h3>
      <p className="case-question">{card.question}</p>
      {card.analysis && (
        <details className="case-analysis">
          <summary>Starts from the published analysis</summary>
          <p>{card.analysis}</p>
        </details>
      )}
      <dl className="case-meta">
        <div>
          <dt>Decision rule</dt>
          <dd>{describeRule(card.decision_rule)}</dd>
        </div>
        <div>
          <dt>Data</dt>
          <dd className="mono">{card.n_rows.toLocaleString("en-US")} rows</dd>
        </div>
      </dl>
      <div className="case-actions">
        {(card.has_recording || card.live_recording) && (
          <button type="button" className="btn btn-primary" onClick={() => onOpenReplay(card.id)}>
            Watch the recorded run
          </button>
        )}
        {liveOnly && !card.has_recording && !card.live_recording && (
          <button type="button" className="btn btn-primary" onClick={() => onOpenReplay(card.id)}>
            See how it runs live
          </button>
        )}
        {!liveOnly && (
          <button type="button" className="btn" disabled={busy !== null} onClick={() => start("scripted")}>
            Replay offline (scripted)
            <span className="btn-note">no model is called</span>
          </button>
        )}
        {liveAvailable && (
          <button type="button" className="btn btn-live" disabled={busy !== null} onClick={() => start("nebius")}>
            Run live on Nemotron
            <span className="btn-note">spends real tokens</span>
          </button>
        )}
      </div>
      {error && (
        <p className="case-error" role="alert">
          {error}
        </p>
      )}
    </article>
  );
}
