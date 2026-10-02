import { useEffect, useState } from "react";
import { getAgent } from "../../shared/api/client";
import type { AgentVersion } from "../../shared/types/contracts";

export type VersionsState =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "ready"; versions: AgentVersion[] };

export function useAgentVersions(agentId: string, enabled: boolean): VersionsState {
  const [state, setState] = useState<VersionsState>({ status: "loading" });
  useEffect(() => {
    if (!enabled) return;
    let active = true;
    getAgent(agentId)
      .then((detail) => active && setState({ status: "ready", versions: detail.versions }))
      .catch((error: unknown) => {
        if (active) setState({ status: "error", message: error instanceof Error ? error.message : "History unavailable" });
      });
    return () => {
      active = false;
    };
  }, [agentId, enabled]);
  return state;
}
