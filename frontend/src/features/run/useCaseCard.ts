import { useEffect, useState } from "react";
import { getCases } from "../../shared/api/client";
import type { CaseCard } from "../../shared/types/contracts";

export function useCaseCard(caseId: string | null): CaseCard | null {
  const [card, setCard] = useState<CaseCard | null>(null);

  useEffect(() => {
    if (!caseId) return;
    let cancelled = false;
    getCases()
      .then((cases) => {
        if (!cancelled) setCard(cases.find((c) => c.id === caseId) ?? null);
      })
      .catch(() => {
        if (!cancelled) setCard(null);
      });
    return () => {
      cancelled = true;
    };
  }, [caseId]);

  return caseId ? card : null;
}
