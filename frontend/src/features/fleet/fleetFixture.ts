import type { AgentCard, AgentCatalog, AgentVersion, AnalysisTemplate, SandboxPolicy } from "../../shared/types/contracts";

export const SANDBOX: SandboxPolicy = {
  executor: "harness",
  require_code_guard: true,
  allowed_commands: ["python"],
  step_dir: "steps",
  data_file: "data.parquet",
  max_timeout_s: 600,
  network: "none",
};

export function sampleCard(partial: Partial<AgentCard> = {}): AgentCard {
  return {
    agent_id: "judge",
    display_name: "Judge",
    purpose: "Scores how defensible each analysis option is.",
    kind: "agent",
    role: "judge",
    model_id: "nvidia/nemotron-3-super-120b-a12b",
    lifecycle: "active",
    department: "decision-analytics",
    owner: "borges-core",
    principal: "agent://borges/judge",
    capabilities: ["dataset.profile.read", "llm.invoke:nvidia/nemotron-3-super-120b-a12b", "spend.use"],
    prompt_sha: "p".repeat(64),
    output_schema_sha: "s".repeat(64),
    code_sha: null,
    policy_sha: "g".repeat(64),
    policy: {
      models: ["nvidia/nemotron-3-super-120b-a12b", "nvidia/Nemotron-3-Ultra-550b-a55b"],
      max_tokens: 2048,
      max_calls_per_run: 400,
      max_cost_usd_per_run: 0.25,
      max_concurrent_calls: 8,
      egress: "profile_only",
      max_sample_rows: 0,
    },
    sandbox_policy: null,
    definition_sha: "d".repeat(64),
    version: "1.1.0",
    approval: "approved",
    latest_version: "1.1.0",
    versions: 2,
    ...partial,
  };
}

export function sampleVersions(): AgentVersion[] {
  return [
    {
      agent_id: "judge",
      version: "1.0.0",
      definition_sha: "o".repeat(64),
      state: "retired",
      bump: "major",
      changelog: "initial definition",
      published_at: 1790000000,
      published_by: "seed",
      history: [],
    },
    {
      agent_id: "judge",
      version: "1.1.0",
      definition_sha: "d".repeat(64),
      state: "approved",
      bump: "minor",
      changelog: "prompt_sha pppppppp -> qqqqqqqq",
      published_at: 1790003600,
      published_by: "operator",
      history: [],
    },
  ];
}

export const TEMPLATE: AnalysisTemplate = {
  id: "checkout_ab",
  title: "New checkout A/B test",
  owner: "borges-core",
  question: "Does the new checkout increase the conversion rate?",
  metric: "conversion lift",
  decision_rule: {
    metric: "conversion lift",
    comparator: "gt",
    threshold: 0,
    alpha: 0.05,
    positive_label: "SHIP",
    negative_label: "DON'T SHIP",
  },
  dataset_name: "checkout_sessions",
  live_only: false,
};

export function sampleCatalog(partial: Partial<AgentCatalog> = {}): AgentCatalog {
  return {
    registry_sha: "r".repeat(64),
    summary: {
      total: 2,
      by_lifecycle: { active: 2 },
      by_approval: { approved: 1, proposed: 1 },
      enforce: true,
      blocked: [],
    },
    agents: [sampleCard(), sampleCard({ agent_id: "harness", display_name: "Harness", kind: "component", approval: "proposed", prompt_sha: null, model_id: "deterministic", policy: null, sandbox_policy: SANDBOX })],
    templates: [TEMPLATE],
    ...partial,
  };
}
