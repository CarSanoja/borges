import { useState } from "react";
import type { AgentCard } from "../../shared/types/contracts";
import { AgentVersions } from "./AgentVersions";
import { AgentPolicyFacts } from "./AgentPolicyFacts";
import { ApprovalBadge } from "./ApprovalBadge";
import { shortSha } from "./fleetFormat";

export function AgentRow({ card }: { card: AgentCard }) {
  const [open, setOpen] = useState(false);
  return (
    <li className="fleet-agent" data-testid={`agent-${card.agent_id}`}>
      <div className="fleet-agent__head">
        <h2 className="fleet-agent__name">{card.display_name}</h2>
        <span className="mono fleet-agent__version">{card.version ? `v${card.version}` : "no version"}</span>
        <ApprovalBadge approval={card.approval} />
        <span className="chip">{card.lifecycle}</span>
        <span className="chip">{card.kind}</span>
      </div>
      <p className="fleet-agent__purpose">{card.purpose}</p>
      <dl className="fleet-agent__facts">
        <div>
          <dt>Model</dt>
          <dd className="mono">{card.model_id}</dd>
        </div>
        <div>
          <dt>Principal</dt>
          <dd className="mono">{card.principal}</dd>
        </div>
        <div>
          <dt>Prompt</dt>
          <dd className="mono" title={card.prompt_sha ?? undefined}>{shortSha(card.prompt_sha)}</dd>
        </div>
        <div>
          <dt>Definition</dt>
          <dd className="mono" title={card.definition_sha}>{shortSha(card.definition_sha)}</dd>
        </div>
        <div>
          <dt>Department</dt>
          <dd>{card.department}</dd>
        </div>
      </dl>
      <AgentPolicyFacts card={card} />
      <ul className="fleet-caps" aria-label="Capabilities">
        {card.capabilities.map((capability) => (
          <li key={capability} className="chip mono">{capability}</li>
        ))}
      </ul>
      <button type="button" className="link-btn" aria-expanded={open} onClick={() => setOpen(!open)}>
        {open ? "Hide version history" : `Version history (${card.versions})`}
      </button>
      {open && <AgentVersions agentId={card.agent_id} currentSha={card.definition_sha} />}
    </li>
  );
}
