import type { MemoryKind, MemorySummary, MemoryUsed } from "../../shared/types/contracts";

export const KIND_LABELS: Record<MemoryKind, string> = {
  verdict: "Judge verdicts",
  code: "Validated code",
  adversary: "Adversary misses",
  note: "Owner notes",
};

export const KINDS = Object.keys(KIND_LABELS) as MemoryKind[];

export function reusedTotal(memory: MemoryUsed | null | undefined): number {
  return memory ? Object.values(memory.reused).reduce((sum, n) => sum + (n ?? 0), 0) : 0;
}

export function reusedSummary(memory: MemoryUsed): string {
  return KINDS.filter((kind) => (memory.reused[kind] ?? 0) > 0)
    .map((kind) => `${memory.reused[kind]} ${KIND_LABELS[kind].toLowerCase()}`)
    .join(", ");
}

export function modeText(summary: MemorySummary): string {
  if (!summary.enabled) return `Memory is off for you: ${summary.note}`;
  if (summary.mode === "public-demo") {
    return summary.encrypted
      ? "Public demo memory: shared by every visitor, curated cases only, encrypted at rest."
      : "Public demo memory: shared by every visitor, curated cases only, stored unencrypted.";
  }
  return "Private memory: encrypted at rest and visible only to your key.";
}

export function totalCount(summary: MemorySummary): number {
  return KINDS.reduce((sum, kind) => sum + (summary.totals[kind] ?? 0), 0);
}

export function shortFingerprint(dataset: string): string {
  return dataset.slice(0, 12);
}
