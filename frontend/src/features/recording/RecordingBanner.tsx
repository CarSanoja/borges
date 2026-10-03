import type { LiveRecordingSummary, RecordingSource, RecordingStamp } from "../../shared/types/contracts";
import { AppLink, replayPath } from "../../shared/router";
import { statementFor, stampStatement } from "./recordingText";
import "./recording.css";

interface Props {
  caseId: string;
  source: RecordingSource;
  live: LiveRecordingSummary | null | undefined;
  hasScripted: boolean;
  stamp?: RecordingStamp | null;
}

export function RecordingBanner({ caseId, source, live, hasScripted, stamp }: Props) {
  const statement = statementFor(source, live);
  const stampText = source === "live" ? stampStatement(stamp) : null;
  const canToggle = Boolean(live) && hasScripted;
  if (!statement && !canToggle) return null;
  return (
    <section className={`recording-banner recording-banner--${source}`} aria-label="Recording source">
      {statement && (
        <p className="recording-statement" role="status" data-testid="recording-statement">
          {statement}
        </p>
      )}
      {stampText && (
        <p className="recording-stamp" data-testid="recording-stamp">
          {stampText}
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
