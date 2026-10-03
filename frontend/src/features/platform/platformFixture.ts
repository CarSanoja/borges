import type { Pillar, PlatformStatus } from "./platformTypes";

function pillar(id: string, name: string, facts: Record<string, unknown>, verify: string, links: Pillar["links"]): Pillar {
  return {
    id,
    name,
    brief: `${name} brief`,
    status: "ok",
    summary: `${name} summary`,
    facts,
    code: [`src/borges/${id}/core.py`],
    tests: [`tests/${id}/test_core.py`],
    verify,
    links,
  };
}

export function samplePlatform(): PlatformStatus {
  return {
    pillars: [
      pillar("registry", "Agent Registry", { agents: 9, approved_versions: 9, registry_sha: "a".repeat(64) }, "borges agents verify", [
        { label: "Fleet", path: "/fleet" },
      ]),
      pillar("runtime", "Agent Runtime", { queue: true, queue_depth: 0, active_workers: 0, dead_letter_count: 0, resume_from_checkpoints: true }, "borges runs dead-letter", [
        { label: "Health", path: "/api/health" },
      ]),
      pillar("memory", "Memory Bank", { enabled: true, encrypted: true, public_demo: { totals: { code: 2 } } }, "borges memory list --tenant public-demo", [
        { label: "Memory", path: "/memory" },
      ]),
      pillar("identity", "Agent Identity", { principal: "caller://anonymous", scopes: ["a"], anonymous_scopes: ["a"] }, "curl -s localhost:8000/api/me", [
        { label: "Who am I", path: "/api/me" },
      ]),
      pillar("gateway", "Agent Gateway", { policy_sha: "b".repeat(64), agents: { judge: {} }, run_max_cost_usd: 0.5 }, "curl -s localhost:8000/api/policy", [
        { label: "Policy", path: "/api/policy" },
      ]),
      pillar("armor", "Model Armor", { screens: ["a", "b"], pii_kinds: ["email"], corpus: { detected: 93, attacks: 93, false_positives: 0 } }, "uv run pytest tests/armor/test_corpus.py -s", [
        { label: "Trace", path: "/api/runs" },
      ]),
      pillar("observability", "Agent Observability", { exporter: "local", audit_chain: { ok: true, records: 4, anchor_present: false } }, "borges audit verify global", [
        { label: "Audit", path: "/api/audit?verify=true" },
      ]),
    ],
  };
}
