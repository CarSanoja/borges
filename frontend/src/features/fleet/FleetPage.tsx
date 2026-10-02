import { AppLink } from "../../shared/router";
import { AgentRow } from "./AgentRow";
import { FleetSummary } from "./FleetSummary";
import { TemplateList } from "./TemplateList";
import { useFleet } from "./useFleet";
import "../trace/trace.css";
import "./fleet.css";

export function FleetPage() {
  const state = useFleet();
  return (
    <main className="fleet-page">
      <header className="trace-header">
        <AppLink to="/" className="run-home">
          Borges
        </AppLink>
        <div className="trace-header__body">
          <p className="eyebrow">Agent registry</p>
          <h1 className="trace-title">Fleet</h1>
        </div>
      </header>
      {state.status === "loading" && <p className="trace-note" role="status">Reading the registry</p>}
      {state.status === "error" && <p className="run-error" role="alert">{state.message}</p>}
      {state.status === "ready" && (
        <>
          <FleetSummary catalog={state.catalog} />
          <ul className="fleet-list" aria-label="Agents">
            {state.catalog.agents.map((card) => (
              <AgentRow key={card.agent_id} card={card} />
            ))}
          </ul>
          <TemplateList templates={state.catalog.templates} />
        </>
      )}
    </main>
  );
}
