import type { AgentCard } from "../../shared/types/contracts";
import { egressLabel, formatUsd, shortSha } from "./fleetFormat";

export function AgentPolicyFacts({ card }: { card: AgentCard }) {
  const { policy, sandbox_policy: sandbox } = card;
  if (!policy && !sandbox) return null;
  return (
    <dl className="fleet-agent__facts fleet-policy" aria-label={`Gateway policy of ${card.agent_id}`}>
      <div>
        <dt>Policy</dt>
        <dd className="mono" title={card.policy_sha ?? undefined}>{shortSha(card.policy_sha)}</dd>
      </div>
      {policy && (
        <>
          <div>
            <dt>Allowed models</dt>
            <dd>
              <ol className="fleet-chain">
                {policy.models.map((model, index) => (
                  <li key={model} className="mono">
                    {model}
                    <span className="chip">{index === 0 ? "primary" : "fallback"}</span>
                  </li>
                ))}
              </ol>
            </dd>
          </div>
          <div>
            <dt>Receives</dt>
            <dd>{egressLabel(policy.egress, policy.max_sample_rows)}</dd>
          </div>
          <div>
            <dt>Per run</dt>
            <dd className="mono">
              {policy.max_calls_per_run} calls, {formatUsd(policy.max_cost_usd_per_run)}, {policy.max_concurrent_calls} at once,
              {" "}{policy.max_tokens} tokens per call
            </dd>
          </div>
        </>
      )}
      {sandbox && (
        <div>
          <dt>Sandbox</dt>
          <dd>
            run only by the {sandbox.executor}
            {sandbox.require_code_guard ? " for code that passed the code guard" : ""}; commands{" "}
            <span className="mono">{sandbox.allowed_commands.join(", ")}</span>, up to {sandbox.max_timeout_s} s,
            network {sandbox.network}
          </dd>
        </div>
      )}
    </dl>
  );
}
