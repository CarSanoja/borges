import type { Health } from "../../shared/types/contracts";
import { liveReasonText } from "./LiveNote";

interface Props {
  health: Health | null;
}

export function HeroMode({ health }: Props) {
  const live = health?.llm_live_available === true;
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
