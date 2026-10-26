import type { MemorySummary, MemoryUsed } from "../../shared/types/contracts";

export function sampleSummary(overrides: Partial<MemorySummary> = {}): MemorySummary {
  return {
    tenant: "public-demo",
    mode: "public-demo",
    enabled: true,
    encrypted: false,
    note: "Shared by all visitors, curated cases only, stored unencrypted.",
    totals: { verdict: 7, code: 11, adversary: 1, note: 0 },
    datasets: [{ dataset: "4738630f2e50aabbccdd", label: "New checkout A/B test", last_used: 1, verdict: 7, code: 11, adversary: 1, note: 0 }],
    limits: {
      verdict: { ttl_days: 90, max_rows: 2000 },
      code: { ttl_days: 30, max_rows: 1000 },
      adversary: { ttl_days: 60, max_rows: 500 },
      note: { ttl_days: 3650, max_rows: 200 },
    },
    ...overrides,
  };
}

export function sampleUsed(overrides: Partial<MemoryUsed> = {}): MemoryUsed {
  return {
    mode: "public-demo",
    encrypted: false,
    dataset: "4738630f2e50",
    reused: { verdict: 6, code: 11, adversary: 1 },
    stored: {},
    sources: [{ run_id: "r_one", count: 18 }],
    dropped: 0,
    ...overrides,
  };
}
