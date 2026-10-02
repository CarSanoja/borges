import type { DecisionRule, Flip, RunSnapshot } from "../../shared/types/contracts";
import { formatNumber } from "./verdictFormat";

export interface FlipKind {
  kind: "direction" | "significance";
  title: string;
  text: string;
}

export interface EffectRange {
  min: number;
  max: number;
  n: number;
}

function onPositiveSide(rule: DecisionRule, estimate: number): boolean {
  return rule.comparator === "gt" ? estimate > rule.threshold : estimate < rule.threshold;
}

function short(value: number): string {
  return Math.abs(value) >= 1 ? value.toFixed(2) : formatNumber(value);
}

function exactP(value: number): string {
  return value < 0.001 ? value.toPrecision(2) : value.toFixed(3);
}

export function describeFlip(rule: DecisionRule, flip: Flip): FlipKind {
  const before = flip.baseline_result;
  const after = flip.flipped_result;
  const estimates = `${short(before.estimate)} to ${short(after.estimate)}`;
  if (onPositiveSide(rule, before.estimate) !== onPositiveSide(rule, after.estimate)) {
    return {
      kind: "direction",
      title: "Direction flip",
      text: `The estimate changes side of the threshold ${rule.threshold}: ${estimates}.`,
    };
  }
  return {
    kind: "significance",
    title: "Significance flip",
    text: `The estimate stays on the same side of the threshold ${rule.threshold} (${estimates}) but p crosses alpha ${rule.alpha}: ${exactP(before.p_value)} to ${exactP(after.p_value)}. The evidence weakens; the effect does not reverse.`,
  };
}

export function effectRange(snapshot: RunSnapshot): EffectRange | null {
  const estimates = Object.values(snapshot.garden.universes)
    .filter((u) => u.status === "done" && u.result !== null && u.kind !== "verification")
    .map((u) => u.result?.estimate ?? Number.NaN)
    .filter((value) => Number.isFinite(value));
  if (estimates.length === 0) return null;
  return { min: Math.min(...estimates), max: Math.max(...estimates), n: estimates.length };
}
