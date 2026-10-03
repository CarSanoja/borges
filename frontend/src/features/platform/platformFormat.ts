import type { Pillar, PillarStatus } from "./platformTypes";

const LABELS: Record<PillarStatus, string> = {
  ok: "Live",
  attention: "Needs attention",
  off: "Off",
  error: "Error",
};

export function statusLabel(status: PillarStatus): string {
  return LABELS[status];
}

export function isInternalPage(path: string): boolean {
  return !path.startsWith("/api/");
}

type Row = [string, string];

const text = (value: unknown): string => (typeof value === "string" ? value : JSON.stringify(value));
const sha = (value: unknown): string => (typeof value === "string" ? value.slice(0, 12) : "");
const count = (value: unknown): string => String(Array.isArray(value) ? value.length : 0);

function runtimeRows(facts: Record<string, unknown>): Row[] {
  if (!facts.queue) return [["queue", "not attached"]];
  return [
    ["queued", text(facts.queue_depth)],
    ["workers", text(facts.active_workers)],
    ["dead-letter", text(facts.dead_letter_count)],
    ["resume", facts.resume_from_checkpoints ? "from checkpoints" : "no"],
  ];
}

function memoryRows(facts: Record<string, unknown>): Row[] {
  const demo = facts.public_demo as { totals?: Record<string, number> } | undefined;
  const total = Object.values(demo?.totals ?? {}).reduce((sum, n) => sum + n, 0);
  const rows: Row[] = [
    ["enabled", text(facts.enabled)],
    ["encrypted", text(facts.encrypted)],
    ["public demo", `${total} memories`],
  ];
  if (typeof facts.tenants === "number") rows.push(["tenants", String(facts.tenants)]);
  return rows;
}

function armorRows(facts: Record<string, unknown>): Row[] {
  const corpus = facts.corpus as { detected: number; attacks: number; false_positives: number } | undefined;
  return [
    ["screens", count(facts.screens)],
    ["pii kinds", count(facts.pii_kinds)],
    ["detected", corpus ? `${corpus.detected} of ${corpus.attacks}` : "n/a"],
    ["false alarms", corpus ? String(corpus.false_positives) : "n/a"],
  ];
}

function observabilityRows(facts: Record<string, unknown>): Row[] {
  const chain = facts.audit_chain as { ok: boolean; records: number; anchor_present: boolean } | undefined;
  return [
    ["exporter", text(facts.exporter)],
    ["audit records", String(chain?.records ?? 0)],
    ["chain", chain?.ok ? "intact" : "broken"],
    ["anchor", chain?.anchor_present ? "present" : "none yet"],
  ];
}

export function factRows(pillar: Pillar): Row[] {
  const facts = pillar.facts;
  switch (pillar.id) {
    case "registry":
      return [
        ["agents", text(facts.agents)],
        ["approved", text(facts.approved_versions)],
        ["registry sha", sha(facts.registry_sha)],
        ...(typeof facts.seeded_approvals === "number" ? ([["seeded approvals", String(facts.seeded_approvals)]] as Row[]) : []),
      ];
    case "runtime":
      return runtimeRows(facts);
    case "memory":
      return memoryRows(facts);
    case "identity":
      return [
        ["you", text(facts.principal)],
        ["scopes", count(facts.scopes)],
        ["anonymous scopes", count(facts.anonymous_scopes)],
        ...(Array.isArray(facts.recent_denials) ? ([["recent denials", String(facts.recent_denials.length)]] as Row[]) : []),
      ];
    case "gateway":
      return [
        ["policy sha", sha(facts.policy_sha)],
        ["agents", String(Object.keys((facts.agents as object | undefined) ?? {}).length)],
        ["run cap", `$${text(facts.run_max_cost_usd)}`],
      ];
    case "armor":
      return armorRows(facts);
    case "observability":
      return observabilityRows(facts);
    default:
      return [];
  }
}
