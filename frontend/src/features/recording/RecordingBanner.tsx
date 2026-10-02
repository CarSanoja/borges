import type { LiveRecordingSummary, RecordingSource } from "../../shared/types/contracts";
import { AppLink, replayPath } from "../../shared/router";
import { statementFor } from "./recordingText";
import "./recording.css";

interface Props {
  caseId: string;
  source: RecordingSource;
  live: LiveRecordingSummary | null | undefined;
  hasScripted: boolean;
}

export function RecordingBanner({ caseId, source, live, hasScripted }: Props) {
  const statement = statementFor(source, live);
  const canToggle = Boolean(live) && hasScripted;
  if (!statement && !canToggle) return null;
  return (
    <section className={`recording-banner recording-banner--${source}`} aria-label="Recording source">
      {statement && (
        <p className="recording-statement" role="status" data-testid="recording-statement">
          {statement}
        </p>
      )}
      {canToggle && (
        <nav className="recording-toggle" aria-label="Choose recording">
          <AppLink
            to={replayPath(caseId)}
            className={`recording-toggle__option${source === "live" ? " is-active" : ""}`}
          >
            Live recording
          </AppLink>
          <AppLink
            to={replayPath(caseId, "scripted")}
            className={`recording-toggle__option${source === "scripted" ? " is-active" : ""}`}
          >
            Scripted replay
          </AppLink>
        </nav>
      )}
    </section>
  );
}
