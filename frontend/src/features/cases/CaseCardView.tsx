import { useState } from "react";
import { createRun } from "../../shared/api/client";
import type { CaseCard } from "../../shared/types/contracts";
import { describeRule } from "./decisionRuleText";

const LIVE_BUDGET_SPENT = "Live budget for this demo is used up";
const LIVE_NEEDS_KEY = "Live mode needs a NEBIUS_API_KEY on the server";

interface Props {
  card: CaseCard;
  liveAvailable: boolean;
  liveUnavailableReason?: "no_key" | "budget_spent" | null;
  onOpenRun: (runId: string) => void;
  onOpenReplay: (caseId: string) => void;
}

export function CaseCardView({ card, liveAvailable, liveUnavailableReason = null, onOpenRun, onOpenReplay }: Props) {
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

  const liveReason =
    liveUnavailableReason === "budget_spent" ? LIVE_BUDGET_SPENT : LIVE_NEEDS_KEY;

  return (
    <article className="case-card">
      <p className="eyebrow">{card.subtitle}</p>
      <h3 className="case-title">{card.title}</h3>
      <p className="case-question">{card.question}</p>
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
        {card.has_recording && (
          <button type="button" className="btn btn-primary" onClick={() => onOpenReplay(card.id)}>
            Watch the recorded run
          </button>
        )}
        <button type="button" className="btn" disabled={busy !== null} onClick={() => start("scripted")}>
          Run it now
        </button>
        <button
          type="button"
          className="btn btn-live"
          disabled={!liveAvailable || busy !== null}
          title={liveAvailable ? "Spends real tokens" : liveReason}
          onClick={() => start("nebius")}
        >
          Run live on Nemotron
          <span className="btn-note">{liveAvailable ? "spends real tokens" : liveReason}</span>
        </button>
      </div>
      {error && (
        <p className="case-error" role="alert">
          {error}
        </p>
      )}
    </article>
  );
}
