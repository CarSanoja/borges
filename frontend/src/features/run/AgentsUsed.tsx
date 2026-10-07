import type { RunAgents } from "../../shared/types/contracts";
import { ApprovalBadge } from "../fleet/ApprovalBadge";
import { shortSha } from "../fleet/fleetFormat";
import { AppLink, FLEET_PATH } from "../../shared/router";

export function AgentsUsed({ agents }: { agents: RunAgents | null | undefined }) {
  if (!agents || agents.agents.length === 0) return null;
  return (
    <details className="run-agents" aria-label="Agents used">
      <summary title={`Agent registry version ${agents.registry_sha}`}>
        Agents used <span className="mono">{agents.agents.length}</span>
      </summary>
      <p className="run-agents__version">
        Agent registry version <span className="mono run-agents__sha" title={agents.registry_sha}>{shortSha(agents.registry_sha)}</span>
      </p>
      <table className="run-agents__table">
        <thead>
          <tr>
            <th scope="col">Agent</th>
            <th scope="col">Version</th>
            <th scope="col">Approval</th>
            <th scope="col">Model</th>
            <th scope="col">Definition</th>
          </tr>
        </thead>
        <tbody>
          {agents.agents.map((use) => (
            <tr key={use.agent_id}>
              <th scope="row">{use.agent_id}</th>
              <td className="mono">{use.version ?? "none"}</td>
              <td>
                <ApprovalBadge approval={use.approval} />
              </td>
              <td className="mono">{use.model_id}</td>
              <td className="mono" title={use.definition_sha}>
                {shortSha(use.definition_sha)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      <AppLink to={FLEET_PATH} className="chip chip--link">
        Open the fleet
      </AppLink>
    </details>
  );
}
