import { CaseCardView } from "./CaseCardView";
import { Hero } from "./Hero";
import { useCases } from "./useCases";
import "./landing.css";

interface Props {
  onOpenRun: (runId: string) => void;
  onOpenReplay: (caseId: string) => void;
  onOpenMock: () => void;
}

export function Landing({ onOpenRun, onOpenReplay, onOpenMock }: Props) {
  const { cases, liveAvailable } = useCases();
  return (
    <main className="landing">
      <Hero />
      <section className="landing-cases" aria-label="Cases">
        {cases.map((card) => (
          <CaseCardView
            key={card.id}
            card={card}
            liveAvailable={liveAvailable}
            onOpenRun={onOpenRun}
            onOpenReplay={onOpenReplay}
          />
        ))}
      </section>
      <p className="landing-mock">
        <button type="button" className="link-btn" onClick={onOpenMock}>
          Open the demo run
        </button>
      </p>
      <footer className="landing-footer">
        Built with NVIDIA Nemotron on Nebius Token Factory · forks run in Nebius Sandboxes
      </footer>
    </main>
  );
}
