import { ApprovalBadge } from "./ApprovalBadge";
import { formatPublished, shortSha } from "./fleetFormat";
import { useAgentVersions } from "./useAgentVersions";

interface Props {
  agentId: string;
  currentSha: string;
}

export function AgentVersions({ agentId, currentSha }: Props) {
  const state = useAgentVersions(agentId, true);
  if (state.status === "loading") return <p className="trace-note" role="status">Reading the history</p>;
  if (state.status === "error") return <p className="run-error" role="alert">{state.message}</p>;
  if (state.versions.length === 0) return <p className="fleet-empty">No version has been published.</p>;
  return (
    <ol className="fleet-versions" aria-label={`Versions of ${agentId}`}>
      {[...state.versions].reverse().map((version) => (
        <li key={version.version} className="fleet-version">
          <span className="mono fleet-version__number">{version.version}</span>
          <ApprovalBadge approval={version.state} />
          {version.definition_sha === currentSha && <span className="chip chip--link">current</span>}
          <span className="fleet-version__log">{version.changelog}</span>
          <span className="mono fleet-version__meta">
            {shortSha(version.definition_sha)} · {version.bump} · {formatPublished(version.published_at)} · {version.published_by}
          </span>
        </li>
      ))}
    </ol>
  );
}
