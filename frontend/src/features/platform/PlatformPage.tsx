import { AppLink } from "../../shared/router";
import { PillarCard } from "./PillarCard";
import { usePlatform } from "./usePlatform";
import "../trace/trace.css";
import "./platform.css";

export function PlatformPage() {
  const state = usePlatform();
  return (
    <main className="platform-page">
      <header className="trace-header">
        <AppLink to="/" className="run-home">
          Borges
        </AppLink>
        <div className="trace-header__body">
          <p className="eyebrow">Enterprise agent fleet</p>
          <h1 className="trace-title">Platform</h1>
        </div>
      </header>
      <p className="platform-lede">
        Seven pillars. Each badge says whether a number is read live from this server or is a fixed measurement with its date. Every card names the command that proves it.
      </p>
      {state.status === "loading" && <p className="trace-note" role="status">Reading the platform</p>}
      {state.status === "error" && <p className="run-error" role="alert">{state.message}</p>}
      {state.status === "ready" && (
        <ul className="platform-grid" aria-label="Pillars">
          {state.platform.pillars.map((pillar) => (
            <PillarCard key={pillar.id} pillar={pillar} />
          ))}
        </ul>
      )}
    </main>
  );
}
