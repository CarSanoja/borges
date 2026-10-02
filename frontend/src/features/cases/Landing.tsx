import type { Health } from "../../shared/types/contracts";
import { backendLabel } from "../run/runLabels";
import { CaseCardView } from "./CaseCardView";
import { Hero } from "./Hero";
import { UploadCard } from "./UploadCard";
import { useCases } from "./useCases";
import "./landing.css";

function footerText(health: Health | null): string {
  if (!health) return "Built with NVIDIA Nemotron";
  const model =
    health.llm === "nebius"
      ? "Built with NVIDIA Nemotron on Nebius Token Factory"
      : "Replays a scripted demo run";
  return `${model} · forks run in ${backendLabel(health.backend)} sandboxes`;
}

interface Props {
  onOpenRun: (runId: string) => void;
  onOpenReplay: (caseId: string) => void;
  onOpenMock: () => void;
}

export function Landing({ onOpenRun, onOpenReplay, onOpenMock }: Props) {
  const { cases, liveAvailable, liveUnavailableReason, health } = useCases();
  const demo = cases.find((card) => card.has_recording);
  const watchDemo = () => (demo ? onOpenReplay(demo.id) : onOpenMock());
  return (
    <main className="landing">
      <Hero onWatchDemo={watchDemo} />
      <section className="landing-cases" aria-label="Cases">
        {cases.map((card) => (
          <CaseCardView
            key={card.id}
            card={card}
            liveAvailable={liveAvailable}
            liveUnavailableReason={liveUnavailableReason}
            onOpenRun={onOpenRun}
            onOpenReplay={onOpenReplay}
          />
        ))}
      </section>
      <UploadCard health={health} onOpenRun={onOpenRun} />
      <p className="landing-mock">
        <button type="button" className="link-btn" onClick={onOpenMock}>
          Open the demo run
        </button>
      </p>
      <footer className="landing-footer">{footerText(health)}</footer>
    </main>
  );
}
