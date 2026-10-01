import type { ReferenceEstimate, RunSnapshot } from "../../shared/types/contracts";

export type PointTone = "baseline" | "agree" | "flip";

export interface CurvePoint {
  id: string;
  kind: string;
  tone: PointTone;
  estimate: number;
  low: number;
  high: number;
  pValue: number;
  verdict: string;
  changed: string[];
  alternatives: Set<string>;
}

export interface MatrixRow {
  stepId: string;
  title: string;
}

function toneOf(kind: string, flipped: boolean | null, verdict: string, baselineVerdict: string | null): PointTone {
  if (kind === "baseline") return "baseline";
  if (flipped !== null) return flipped ? "flip" : "agree";
  return baselineVerdict !== null && verdict !== baselineVerdict ? "flip" : "agree";
}

export function buildPoints(snapshot: RunSnapshot): CurvePoint[] {
  const universes = Object.values(snapshot.garden.universes);
  const baselineVerdict = universes.find((u) => u.kind === "baseline")?.verdict ?? null;
  const defaults = new Map(
    (snapshot.plan?.steps ?? []).map((s) => [s.id, s.options.find((o) => o.is_default)?.id ?? null]),
  );
  const points: CurvePoint[] = [];
  for (const u of universes) {
    if (u.status !== "done" || u.result === null || u.kind === "verification") continue;
    const verdict = u.verdict ?? "";
    const alternatives = new Set(
      defaults.size > 0
        ? Object.entries(u.choices)
            .filter(([stepId, optionId]) => defaults.has(stepId) && defaults.get(stepId) !== optionId)
            .map(([stepId]) => stepId)
        : u.changed,
    );
    points.push({
      id: u.id,
      kind: u.kind,
      tone: toneOf(u.kind, u.flipped, verdict, baselineVerdict),
      estimate: u.result.estimate,
      low: u.result.ci_low,
      high: u.result.ci_high,
      pValue: u.result.p_value,
      verdict,
      changed: u.changed,
      alternatives,
    });
  }
  return points.sort((a, b) => a.estimate - b.estimate);
}

export function buildRows(snapshot: RunSnapshot, points: readonly CurvePoint[]): MatrixRow[] {
  if (snapshot.plan) return snapshot.plan.steps.map((s) => ({ stepId: s.id, title: s.title }));
  const ids = new Set(points.flatMap((p) => [...p.alternatives]));
  return [...ids].map((stepId) => ({ stepId, title: stepId }));
}

export function yDomain(
  points: readonly CurvePoint[],
  threshold: number | null,
  reference: readonly ReferenceEstimate[],
): [number, number] {
  const values: number[] = threshold === null ? [] : [threshold];
  for (const p of points) values.push(p.low, p.high, p.estimate);
  for (const r of reference) values.push(r.estimate, r.ci_low ?? r.estimate, r.ci_high ?? r.estimate);
  if (values.length === 0) return [-1, 1];
  const min = Math.min(...values);
  const max = Math.max(...values);
  const pad = (max - min || Math.abs(max) || 1) * 0.08;
  return [min - pad, max + pad];
}

export function titleFor(rows: readonly MatrixRow[], stepId: string): string {
  return rows.find((r) => r.stepId === stepId)?.title ?? stepId;
}
