import type { AgentCatalog } from "../../shared/types/contracts";
import { shortSha } from "./fleetFormat";

export function FleetSummary({ catalog }: { catalog: AgentCatalog }) {
  const { summary } = catalog;
  return (
    <>
      <dl className="trace-summary" aria-label="Fleet summary">
        <div>
          <dt>Agents</dt>
          <dd className="mono">{summary.total}</dd>
        </div>
        {Object.entries(summary.by_approval).map(([state, count]) => (
          <div key={state}>
            <dt>{state}</dt>
            <dd className="mono">{count}</dd>
          </div>
        ))}
        <div>
          <dt>Registry</dt>
          <dd className="mono" title={catalog.registry_sha}>{shortSha(catalog.registry_sha)}</dd>
        </div>
        <div>
          <dt>Live runs</dt>
          <dd>{summary.enforce ? "gated by approval" : "not gated"}</dd>
        </div>
      </dl>
      {summary.blocked.length > 0 && (
        <p className="run-error" role="alert">
          Live runs are {summary.enforce ? "blocked" : "not approved"} for:{" "}
          {summary.blocked.map((item) => `${item.agent_id} (${item.reason})`).join(", ")}
        </p>
      )}
    </>
  );
}
