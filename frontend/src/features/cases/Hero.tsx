import "./hero.css";
import type { Health } from "../../shared/types/contracts";
import { HeroGarden } from "./HeroGarden";
import { HeroMode } from "./HeroMode";

const STEPS = [
  { n: "I", title: "Fork", text: "Every defensible choice becomes a real sandbox fork of the analysis." },
  { n: "II", title: "Argue", text: "An adversary argues against the conclusion, with code, on the actual data." },
  { n: "III", title: "Flip", text: "Borges finds the one defensible change that changes the decision." },
];

export const PITCH =
  "Borges stress-tests a data conclusion for analysts and data teams: it forks every defensible analysis choice in real sandboxes and shows the one that flips your decision.";

interface Props {
  onWatchDemo: () => void;
  health: Health | null;
  healthLoaded: boolean;
}

export function Hero({ onWatchDemo, health, healthLoaded }: Props) {
  return (
    <header className="landing-hero">
      <div className="landing-copy">
        <p className="eyebrow">Borges · The garden of forking paths</p>
        <h1 className="landing-title">Every conclusion is one path through a garden.</h1>
        <p className="landing-pitch">{PITCH}</p>
        <div className="landing-cta">
          <button type="button" className="btn btn-primary btn-cta" onClick={onWatchDemo}>
            Watch the 30-second demo
          </button>
          {health?.uploads_available === true && (
            <a className="btn btn-cta" href="#bring-your-own-data">
              Bring your own data
            </a>
          )}
        </div>
        {healthLoaded && <HeroMode health={health} />}
        <p className="landing-sub">29 research teams. Same data. Opposite answers.</p>
      </div>
      <HeroGarden />
      <ol className="landing-steps">
        {STEPS.map((step) => (
          <li key={step.n}>
            <span className="landing-step-n">{step.n}</span>
            <h2>{step.title}</h2>
            <p>{step.text}</p>
          </li>
        ))}
      </ol>
    </header>
  );
}
