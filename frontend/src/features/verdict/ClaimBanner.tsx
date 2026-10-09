import type { ClaimCheck } from "../../shared/types/contracts";

export function ClaimBanner({ check }: { check: ClaimCheck | null | undefined }) {
  if (!check || check.agrees !== false) return null;
  return (
    <p className="vc-claim" role="alert" data-testid="claim-check">
      <strong>The claim in your text does not reproduce</strong>
      {check.sentence}
    </p>
  );
}
