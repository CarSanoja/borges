export type Comparator = "gt" | "lt";

export interface DecisionRule {
  metric: string;
  comparator: Comparator;
  threshold: number;
  alpha: number;
  positive_label: string;
  negative_label: string;
}

export interface ColumnProfile {
  name: string;
  dtype: string;
  n_missing: number;
  n_unique: number;
  summary: Record<string, number | string>;
}

export interface DatasetProfile {
  name: string;
  n_rows: number;
  columns: ColumnProfile[];
  sample_rows: Record<string, unknown>[];
}

export type StepKind = "filter" | "transform" | "feature" | "model";
export type OptionOrigin = "planner" | "adversary" | "pinned";

export interface Option {
  id: string;
  label: string;
  rationale: string;
  spec: string;
  is_default: boolean;
  origin: OptionOrigin;
  source: string | null;
  defensibility: number | null;
  code: string | null;
}

export interface Step {
  id: string;
  title: string;
  kind: StepKind;
  description: string;
  options: Option[];
}

export interface AnalysisPlan {
  question: string;
  estimand: string;
  decision_rule: DecisionRule;
  dataset: DatasetProfile;
  steps: Step[];
}

export interface AnalysisResult {
  estimate: number;
  ci_low: number;
  ci_high: number;
  p_value: number;
  n: number;
  metric: string;
  extra: Record<string, number>;
}

export interface StepTrace {
  step_id: string;
  option_id: string;
  rows_before: number;
  rows_after: number;
  note: string;
}

export type UniverseKind = "baseline" | "single" | "adversary" | "combination" | "verification";
export type UniverseStatus = "pending" | "running" | "done" | "failed";

export interface Universe {
  id: string;
  choices: Record<string, string>;
  changed: string[];
  kind: UniverseKind;
  status: UniverseStatus;
  result: AnalysisResult | null;
  verdict: string | null;
  flipped: boolean | null;
  checkpoints: string[];
  traces: StepTrace[];
  error: string | null;
  duration_s: number;
}

export interface Change {
  step_id: string;
  step_title: string;
  from_option: string;
  to_option: string;
  to_label: string;
  rationale: string;
  source: string | null;
  defensibility: number | null;
}

export interface Flip {
  universe_id: string;
  changes: Change[];
  baseline_result: AnalysisResult;
  flipped_result: AnalysisResult;
  baseline_verdict: string;
  flipped_verdict: string;
  reproduced: boolean | null;
  reproduce_command: string | null;
  kind?: "direction" | "significance" | null;
  estimand_change?: string | null;
  contaminated?: boolean;
  contamination_reason?: string | null;
}

export interface DecisionInfluence {
  step_id: string;
  title: string;
  mean_abs_delta: number;
  max_abs_delta: number;
  flips: number;
  n_alternatives: number;
}

export interface SearchSummary {
  levels_explored: number;
  max_combinations_per_level: number;
  universe_budget: number;
  universes_used: number;
  budget_exhausted: boolean;
}

export interface CodingSummary {
  options: number;
  smoke_tested: number;
  repaired_after_smoke: number;
  failed: number;
  options_dropped_by_judge?: number;
  defaults_replaced?: string[];
  defaults_disputed?: string[];
  options_dropped_by_armor?: number;
}

export interface PiiColumn {
  column: string;
  kinds: Record<string, number>;
  scanned: number;
  total_rows: number;
}

export interface PiiSummary {
  columns: PiiColumn[];
  total_detections: number;
  note: string;
}

export interface Report {
  question: string;
  original_verdict: string;
  original_result: AnalysisResult;
  minimal_flip: Flip | null;
  influences: DecisionInfluence[];
  robustness: number;
  n_universes: number;
  n_flipped: number;
  n_distinct_results?: number;
  robustness_rating?: number | null;
  robustness_rating_reason?: string | null;
  robustness_basis?: "design_weighted" | "distinct_results" | "none";
  narrative: string;
  caveats: string[];
  n_failed?: number;
  failed?: string[];
  search?: SearchSummary | null;
  coding?: CodingSummary | null;
  agents?: RunAgents | null;
}

export interface Garden {
  baseline_id: string | null;
  universes: Record<string, Universe>;
}

export interface ReferenceEstimate {
  label: string;
  estimate: number;
  ci_low: number | null;
  ci_high: number | null;
  significant: boolean | null;
}

export type RecordingSource = "live" | "scripted";

export interface LiveRecordingSummary {
  recorded_at: string;
  models: Record<string, string>;
  llm_calls: number;
  tokens_in: number;
  tokens_out: number;
  cost_usd: number;
  verdict: string;
  flipped_verdict: string | null;
  flip_kind: "direction" | "significance" | null;
  universes: number;
  baseline?: ResultBrief | null;
  flipped?: ResultBrief | null;
  flip_changes?: string[];
  contaminated?: boolean;
  estimand_change?: string | null;
}

export interface RecordingStamp {
  run_id?: string | null;
  case_id?: string | null;
  recorded_at?: string | null;
  commit?: string | null;
  dirty?: boolean | null;
  llm?: string | null;
  backend?: string | null;
  registry_sha?: string | null;
  cost_usd?: number | null;
  n_universes?: number | null;
  verdict?: string | null;
  flipped_verdict?: string | null;
}

export interface ResultBrief {
  estimate: number;
  ci_low: number;
  ci_high: number;
  p_value: number;
  n: number;
}

export interface CaseCard {
  id: string;
  title: string;
  subtitle: string;
  question: string;
  decision_rule: DecisionRule;
  n_rows: number;
  has_recording: boolean;
  reference_label: string | null;
  reference: ReferenceEstimate[];
  story: string;
  live_only?: boolean;
  provenance?: string;
  traced_sources?: RecordingSource[];
  live_recording?: LiveRecordingSummary | null;
  recording_meta?: Partial<Record<RecordingSource, RecordingStamp>>;
}

export type StageName =
  | "profiling"
  | "planning"
  | "coding"
  | "baseline"
  | "single_flips"
  | "adversary"
  | "combination_flips"
  | "verifying"
  | "narrating";

export type RunStatus = "queued" | "running" | "completed" | "failed" | "cancelled";

export interface CheckpointNode {
  checkpoint_id: string;
  parent_id: string | null;
  step_id: string | null;
  option_id: string | null;
  depth: number;
}

export interface UsageSnapshot {
  tokens_in: number;
  tokens_out: number;
  cost_usd: number;
  llm_calls: number;
  cached_calls: number;
  checkpoints: number;
  universes: number;
}

export interface RunSnapshot {
  run_id: string;
  status: RunStatus;
  case_id: string | null;
  title: string;
  question: string;
  decision_rule: DecisionRule | null;
  llm?: "nebius" | "scripted" | "local" | null;
  backend?: string | null;
  stages: Partial<Record<StageName, "started" | "done">>;
  plan: AnalysisPlan | null;
  checkpoints: CheckpointNode[];
  garden: Garden;
  flip: Flip | null;
  report: Report | null;
  usage: UsageSnapshot;
  error: string | null;
  agents?: RunAgents | null;
  resumed?: number;
  memory?: MemoryUsed | null;
  last_seq: number;
}

export interface RunRequest {
  case_id?: string | null;
  upload_id?: string | null;
  question?: string | null;
  decision_rule?: DecisionRule | null;
  llm?: "nebius" | "scripted" | "local" | null;
  backend?: "local" | "contree" | null;
  max_universes?: number | null;
}

export interface RunCreated {
  run_id: string;
}

export interface RunSummary {
  run_id: string;
  case_id: string | null;
  title: string;
  status: RunStatus;
  created_at: number;
  llm: string;
  backend: string;
  cost_usd: number;
  n_universes: number;
  verdict: string | null;
  flipped_verdict: string | null;
}

export interface UniverseStepDetail {
  step: Step;
  option: Option;
  trace: StepTrace | null;
  changed: boolean;
  checkpoint_id: string | null;
}

export interface UniverseDetail {
  universe: Universe;
  steps: UniverseStepDetail[];
  reproduce_command: string;
  reproduce_kind?: "case" | "script";
  script_url?: string | null;
  script_filename?: string | null;
}

export interface Me {
  principal: string;
  kind: "anonymous" | "key" | "legacy";
  anonymous: boolean;
  scopes: string[];
  key_id: string | null;
  expires_at: number | null;
  rate_limit: { limit: number; remaining: number; refill_per_s: number };
}

export interface Health {
  status: "ok";
  llm: "nebius" | "scripted" | "local";
  llm_live_available: boolean;
  backend: string;
  spend_usd: number;
  spend_cap_usd: number;
  live_unavailable_reason?: "no_key" | "budget_spent" | null;
  uploads_available?: boolean;
  uploads_unavailable_reason?: string | null;
  queue_depth?: number;
  active_workers?: number;
  oldest_job_age_s?: number | null;
  dead_letter_count?: number;
}

interface EventBase<T extends string, D> {
  seq: number;
  ts: number;
  run_id: string;
  type: T;
  data: D;
}

export type RunEvent =
  | EventBase<
      "run.started",
      {
        case_id: string | null;
        title: string;
        question: string;
        decision_rule: DecisionRule;
        mode: "live" | "replay";
        llm: "nebius" | "scripted" | "local";
        backend: string;
        models: Record<string, string>;
        max_universes: number;
        trace_id?: string | null;
      }
    >
  | EventBase<"stage", { name: StageName; status: "started" | "done"; detail: string }>
  | EventBase<"plan.ready", { plan: AnalysisPlan }>
  | EventBase<
      "option.coded",
      { step_id: string; option_id: string; ok: boolean; attempts: number; error: string | null }
    >
  | EventBase<
      "option.smoke",
      {
        step_id: string;
        option_id: string;
        status: "passed" | "repaired" | "failed";
        attempts: number;
        error: string | null;
      }
    >
  | EventBase<"option.proposed", { step_id: string; option: Option }>
  | EventBase<
      "option.judged",
      { step_id: string; option_id: string; defensibility: number; accepted: boolean; reason: string; origin?: "planner" | "adversary" }
    >
  | EventBase<
      "checkpoint.created",
      {
        checkpoint_id: string;
        parent_id: string | null;
        step_id: string | null;
        option_id: string | null;
        depth: number;
        duration_s: number;
      }
    >
  | EventBase<"universe.started", { universe: Universe }>
  | EventBase<"universe.finished", { universe: Universe }>
  | EventBase<"flip.found", { flip: Flip }>
  | EventBase<"flip.verified", { flip: Flip }>
  | EventBase<"usage", UsageSnapshot>
  | EventBase<"report.ready", { report: Report }>
  | EventBase<"run.finished", { status: "completed" | "failed" | "cancelled"; elapsed_s: number }>
  | EventBase<"run.failed", { error: string }>
  | EventBase<"memory.used", MemoryUsed>
  | EventBase<"run.resumed", { reason: string; restored_universes: number; dropped_events: number }>
  | EventBase<"run.cancelled", { reason: string }>;

export type RunEventType = RunEvent["type"];

export type MemoryKind = "verdict" | "code" | "adversary" | "note";

export interface MemoryUsed {
  mode: "public-demo" | "keyed" | "off";
  encrypted: boolean;
  dataset: string;
  reused: Partial<Record<MemoryKind, number>>;
  stored: Partial<Record<MemoryKind, number>>;
  sources: { run_id: string; count: number }[];
  dropped: number;
}

export interface MemoryDataset {
  dataset: string;
  last_used: number;
  verdict: number;
  code: number;
  adversary: number;
  note: number;
}

export interface MemorySummary {
  tenant: string;
  mode: "public-demo" | "keyed" | "off";
  enabled: boolean;
  encrypted: boolean;
  note: string;
  totals: Record<MemoryKind, number>;
  datasets: MemoryDataset[];
  limits: Record<MemoryKind, { ttl_days: number; max_rows: number }>;
}

export interface MemoryForgotten {
  tenant: string;
  dataset: string | null;
  removed: Record<MemoryKind, number>;
}

export interface AuditRecord {
  v: number;
  seq: number;
  ts: string;
  kind: string;
  run_id: string | null;
  trace_id: string | null;
  span_id: string | null;
  principal: string | null;
  decision: "allow" | "deny" | "observe" | null;
  reason: string | null;
  data: Record<string, unknown>;
  prev_hash: string;
  hash: string;
}

export interface AuditChainStatus {
  path: string;
  exists: boolean;
  ok: boolean;
  records: number;
  head_hash: string;
  broken_seq: number | null;
  broken_line: number | null;
  reason: string | null;
}

export type SpanAttributeValue = string | number | boolean;

export interface SpanNode {
  span_id: string;
  parent_span_id: string | null;
  name: string;
  kind: string | null;
  status: string;
  start_ns: number;
  end_ns: number | null;
  duration_ms: number | null;
  attributes: Record<string, SpanAttributeValue>;
  audit: AuditRecord[];
  children: SpanNode[];
}

export interface TraceResponse {
  run_id: string;
  trace_id: string | null;
  span_count: number;
  spans_by_kind: Record<string, number>;
  roots: SpanNode[];
  unlinked_audit: AuditRecord[];
  audit_chain: AuditChainStatus | null;
  reason: string | null;
}

export type AgentLifecycle = "active" | "shadow" | "retired";
export type AgentApproval = "proposed" | "approved" | "retired" | "unpublished";

export interface AgentUse {
  agent_id: string;
  version: string | null;
  definition_sha: string;
  approval: AgentApproval;
  model_id: string;
  prompt_sha: string | null;
  principal: string;
  lifecycle: AgentLifecycle;
  policy_sha?: string | null;
}

export interface RunAgents {
  registry_sha: string;
  agents: AgentUse[];
  policy_sha?: string | null;
}

export type EgressClass = "none" | "profile_only" | "sample_rows";

export interface AgentPolicy {
  models: string[];
  max_tokens: number;
  max_calls_per_run: number;
  max_cost_usd_per_run: number;
  max_concurrent_calls: number;
  egress: EgressClass;
  max_sample_rows: number;
}

export interface SandboxPolicy {
  executor: string;
  require_code_guard: boolean;
  allowed_commands: string[];
  step_dir: string;
  data_file: string;
  max_timeout_s: number;
  network: "none";
}

export interface AgentCard {
  agent_id: string;
  display_name: string;
  purpose: string;
  kind: "agent" | "component";
  role: string;
  model_id: string;
  lifecycle: AgentLifecycle;
  department: string;
  owner: string;
  principal: string;
  capabilities: string[];
  prompt_sha: string | null;
  output_schema_sha: string | null;
  code_sha: string | null;
  policy_sha: string | null;
  policy: AgentPolicy | null;
  sandbox_policy: SandboxPolicy | null;
  definition_sha: string;
  version: string | null;
  approval: AgentApproval;
  latest_version: string | null;
  versions: number;
}

export interface AnalysisTemplate {
  id: string;
  title: string;
  owner: string;
  question: string;
  metric: string;
  decision_rule: DecisionRule;
  dataset_name: string;
  live_only: boolean;
}

export interface RegistryBlocker {
  agent_id: string;
  definition_sha: string;
  reason: string;
}

export interface AgentCatalog {
  registry_sha: string;
  summary: {
    total: number;
    by_lifecycle: Record<string, number>;
    by_approval: Record<string, number>;
    enforce: boolean;
    blocked: RegistryBlocker[];
  };
  agents: AgentCard[];
  templates: AnalysisTemplate[];
}

export interface AgentTransition {
  ts: number;
  state: AgentApproval;
  by: string;
  reason: string | null;
}

export interface AgentVersion {
  agent_id: string;
  version: string;
  definition_sha: string;
  state: AgentApproval;
  bump: string;
  changelog: string;
  published_at: number;
  published_by: string;
  history: AgentTransition[];
}

export interface AgentDetail {
  card: AgentCard;
  versions: AgentVersion[];
}
