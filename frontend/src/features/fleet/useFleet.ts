import { useEffect, useState } from "react";
import { getAgents } from "../../shared/api/client";
import type { AgentCatalog } from "../../shared/types/contracts";

export type FleetState =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "ready"; catalog: AgentCatalog };

export function useFleet(): FleetState {
  const [state, setState] = useState<FleetState>({ status: "loading" });
  useEffect(() => {
    let active = true;
    getAgents()
      .then((catalog) => active && setState({ status: "ready", catalog }))
      .catch((error: unknown) => {
        if (active) setState({ status: "error", message: error instanceof Error ? error.message : "Registry unavailable" });
      });
    return () => {
      active = false;
    };
  }, []);
  return state;
}
