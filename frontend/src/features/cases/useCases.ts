import { useEffect, useState } from "react";
import { getCases, getHealth } from "../../shared/api/client";
import type { CaseCard, Health } from "../../shared/types/contracts";
import { FALLBACK_CASES } from "./fallbackCases";

interface CasesState {
  cases: CaseCard[];
  liveAvailable: boolean;
  liveUnavailableReason: Health["live_unavailable_reason"];
  health: Health | null;
  healthLoaded: boolean;
  offline: boolean;
}

export function useCases(): CasesState {
  const [state, setState] = useState<CasesState>({ cases: FALLBACK_CASES, liveAvailable: false, liveUnavailableReason: null, health: null, healthLoaded: false, offline: false });

  useEffect(() => {
    let active = true;
    getCases().then(
      (cases) => {
        if (active && cases.length > 0) setState((prev) => ({ ...prev, cases, offline: false }));
      },
      () => {
        if (active) setState((prev) => ({ ...prev, offline: true }));
      },
    );
    getHealth().then(
      (health) => {
        if (active) setState((prev) => ({
            ...prev,
            health,
            healthLoaded: true,
            liveAvailable: health.llm_live_available,
            liveUnavailableReason: health.live_unavailable_reason ?? null,
          }));
      },
      () => {
        if (active) setState((prev) => ({ ...prev, healthLoaded: true }));
      },
    );
    return () => {
      active = false;
    };
  }, []);

  return state;
}
