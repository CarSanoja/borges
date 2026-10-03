import type { CaseCard } from "../../shared/types/contracts";
import { provenanceKind } from "./ProvenanceChip";

export interface Headline {
  card: CaseCard;
  mechanics: boolean;
}

function score(card: CaseCard): number {
  const live = card.live_recording;
  if (!live) return -1;
  const real = card.provenance ? provenanceKind(card.provenance) === "real" : false;
  const flipped = live.flipped_verdict !== null && live.flipped_verdict !== undefined;
  return (
    (real ? 8 : 0) +
    (flipped ? 4 : 0) +
    (live.contaminated ? -6 : 0) +
    (live.estimand_change ? -2 : 0)
  );
}

export function pickHeadline(cases: readonly CaseCard[]): Headline | null {
  const live = cases.filter((card) => card.live_recording);
  const best = [...live].sort((a, b) => score(b) - score(a))[0];
  if (best) return { card: best, mechanics: false };
  const scripted = cases.find((card) => card.has_recording);
  return scripted ? { card: scripted, mechanics: true } : null;
}
