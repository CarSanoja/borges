import type { Health } from "../../shared/types/contracts";
import { backendLabel } from "../run/runLabels";
import { AppLink, FLEET_PATH, MEMORY_PATH, PLATFORM_PATH } from "../../shared/router";
import { CaseCardView } from "./CaseCardView";
import { Hero } from "./Hero";
import { HeadlineResult } from "./HeadlineResult";
import { pickHeadline } from "./headline";
import { LiveNote } from "./LiveNote";
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
  const { cases: allCases, liveAvailable, health, healthLoaded } = useCases();
  const cases = [...allCases].sort((a, b) => Number(a.live_only === true) - Number(b.live_only === true));
  const liveOnlyCases = allCases.filter((card) => card.live_only);
  const headline = pickHeadline(cases);
  const liveDemo = headline && !headline.mechanics ? headline.card : undefined;
  const demo = headline?.card;
  const watchDemo = () => (demo ? onOpenReplay(demo.id) : onOpenMock());
  return (
    <main className="landing">
      <nav className="landing-nav" aria-label="Main">
        <AppLink to={FLEET_PATH} className="chip chip--link">
          Fleet
        </AppLink>
        <AppLink to={MEMORY_PATH} className="chip chip--link">
          Memory
        </AppLink>
        <AppLink to={PLATFORM_PATH} className="chip chip--link">
          Platform
        </AppLink>
      </nav>
      <Hero
        onWatchDemo={watchDemo}
        health={health}
        healthLoaded={healthLoaded}
        liveRecording={liveDemo?.live_recording}
        headline={headline ? <HeadlineResult headline={headline} onOpen={onOpenReplay} /> : null}
      />
      {healthLoaded && <UploadCard health={health} onOpenRun={onOpenRun} />}
      {healthLoaded && !liveAvailable && <LiveNote health={health} liveOnlyCases={liveOnlyCases} />}
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
      <footer className="landing-footer">{footerText(health)}</footer>
    </main>
  );
}
