import type { Health, LiveRecordingSummary } from "../../shared/types/contracts";
import { liveStatement } from "../recording/recordingText";
import { liveReasonText } from "./LiveNote";

interface Props {
  health: Health | null;
  liveRecording?: LiveRecordingSummary | null;
}

export function HeroMode({ health, liveRecording }: Props) {
  const live = health?.llm_live_available === true;
  if (liveRecording) {
    return (
      <p className="landing-mode landing-mode--live" role="status" aria-label="Run mode" data-testid="hero-live-recording">
        <strong>{liveStatement(liveRecording)}</strong>
      </p>
    );
  }
  return (
    <p className={`landing-mode ${live ? "landing-mode--live" : "landing-mode--scripted"}`} role="status" aria-label="Run mode">
      {live ? (
        <>
          <strong>Live on Nemotron</strong> · runs on this server call NVIDIA Nemotron on Nebius Token Factory.
        </>
      ) : (
        <>
          <strong>Recorded scripted replays: no model is called on this server</strong> · {liveReasonText(health)}.
        </>
      )}
    </p>
  );
}
