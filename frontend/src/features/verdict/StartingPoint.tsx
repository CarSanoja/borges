import type { ReferenceCheck } from "../../shared/types/contracts";

const LINES: Record<ReferenceCheck, string> = {
  agrees: "Checked: two independent implementations of your analysis give this same result.",
  repaired:
    "Repaired: the step-by-step code departed from your analysis and was fixed to match two independent implementations of it.",
  disagrees:
    "Not your analysis: two independent implementations of it give a different result. Read this result with care.",
  unresolved: "Unconfirmed: independent implementations of your analysis disagreed with each other.",
  unchecked: "Not checked against an independent implementation of your analysis.",
};

const TONES: Record<ReferenceCheck, "ok" | "warn"> = {
  agrees: "ok",
  repaired: "ok",
  disagrees: "warn",
  unresolved: "warn",
  unchecked: "warn",
};

export function StartingPoint({ check }: { check: ReferenceCheck | null | undefined }) {
  if (!check) return null;
  return (
    <p className="vc-start" data-tone={TONES[check]} data-testid="starting-point">
      <span className="vc-start__label">Starting point</span> {LINES[check]}
    </p>
  );
}
