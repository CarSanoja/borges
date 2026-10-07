import { formatNumber } from "../verdict/verdictFormat";

export const IMMATERIAL_SHARE_OF_LARGEST_SHIFT = 0.01;
export const IMMATERIAL_SHARE_OF_BASELINE_ESTIMATE = 0.01;

export const NO_MATERIAL_EFFECT = "no material effect";

export interface ShiftContext {
  largestShift: number;
  baselineEstimate: number | null;
  flips: number;
}

export function isImmaterialShift(shift: number, context: ShiftContext): boolean {
  if (context.flips > 0) return false;
  const belowLargest = shift < context.largestShift * IMMATERIAL_SHARE_OF_LARGEST_SHIFT;
  const baseline = context.baselineEstimate;
  const belowBaseline =
    baseline !== null && baseline !== 0 && shift < Math.abs(baseline) * IMMATERIAL_SHARE_OF_BASELINE_ESTIMATE;
  return belowLargest || belowBaseline;
}

export function describeShift(shift: number, context: ShiftContext): string {
  return isImmaterialShift(shift, context) ? NO_MATERIAL_EFFECT : formatNumber(shift);
}
