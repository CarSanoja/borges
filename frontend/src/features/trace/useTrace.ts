import { useEffect, useState } from "react";
import { getTrace } from "../../shared/api/client";
import type { TraceResponse } from "../../shared/types/contracts";

export type TraceState =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "ready"; trace: TraceResponse };

export function useTrace(runId: string): TraceState {
  const [state, setState] = useState<TraceState>({ status: "loading" });
  useEffect(() => {
    let active = true;
    setState({ status: "loading" });
    getTrace(runId)
      .then((trace) => active && setState({ status: "ready", trace }))
      .catch((error: unknown) => {
        if (active) setState({ status: "error", message: error instanceof Error ? error.message : "Trace unavailable" });
      });
    return () => {
      active = false;
    };
  }, [runId]);
  return state;
}
