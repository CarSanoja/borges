import type { AuditChainStatus } from "../../shared/types/contracts";
import { shortHash } from "./spanFormat";

interface Props {
  chain: AuditChainStatus | null;
}

export function chainState(chain: AuditChainStatus | null): "verified" | "broken" | "none" {
  if (!chain || !chain.exists || chain.records === 0) return "none";
  return chain.ok ? "verified" : "broken";
}

export function ChainBadge({ chain }: Props) {
  const state = chainState(chain);
  if (state === "none" || !chain) {
    return (
      <span className="chip trace-chain" data-state="none" role="status">
        No audit chain
      </span>
    );
  }
  if (state === "broken") {
    return (
      <span
        className="chip trace-chain"
        data-state="broken"
        role="status"
        title={chain.reason ?? undefined}
      >
        Audit chain broken at record {chain.broken_seq}
      </span>
    );
  }
  return (
    <span
      className="chip trace-chain"
      data-state="verified"
      role="status"
      title={`head ${chain.head_hash}`}
    >
      Audit chain verified · {chain.records} records · {shortHash(chain.head_hash)}
    </span>
  );
}
