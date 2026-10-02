import type { CaseCard, Health } from "../../shared/types/contracts";

const REASONS: Record<string, string> = {
  budget_spent: "the live budget for this demo is used up",
  no_key: "the server has no NEBIUS_API_KEY",
};

export function liveReasonText(health: Health | null): string {
  if (!health) return "the server is not reachable";
  const code = health.live_unavailable_reason;
  return (code && REASONS[code]) || "live mode is not enabled on this server";
}

interface Props {
  health: Health | null;
  hiddenCases: CaseCard[];
}

export function LiveNote({ health, hiddenCases }: Props) {
  const needs = hiddenCases.length
    ? ` ${hiddenCases.length === 1 ? "One case needs" : `${hiddenCases.length} cases need`} live mode: ${hiddenCases.map((card) => card.title).join(", ")}.`
    : "";
  return (
    <p className="landing-live-note" role="status" aria-label="Live mode">
      Live runs are off here: {liveReasonText(health)}. The recorded and scripted runs below work.{needs}
    </p>
  );
}
