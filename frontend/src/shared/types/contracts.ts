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
}

export interface DecisionInfluence {
  step_id: string;
  title: string;
  mean_abs_delta: number;
  max_abs_delta: number;
  flips: number;
  n_alternatives: number;
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
  narrative: string;
  caveats: string[];
  n_failed?: number;
  failed?: string[];
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

export type RunStatus = "running" | "completed" | "failed";

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
  llm?: "nebius" | "scripted" | null;
  backend?: string | null;
  stages: Partial<Record<StageName, "started" | "done">>;
  plan: AnalysisPlan | null;
  checkpoints: CheckpointNode[];
  garden: Garden;
  flip: Flip | null;
  report: Report | null;
  usage: UsageSnapshot;
  error: string | null;
  last_seq: number;
}

export interface RunRequest {
  case_id?: string | null;
  upload_id?: string | null;
  question?: string | null;
  decision_rule?: DecisionRule | null;
  llm?: "nebius" | "scripted" | null;
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
}

export interface Health {
  status: "ok";
  llm: "nebius" | "scripted";
  llm_live_available: boolean;
  backend: string;
  spend_usd: number;
  spend_cap_usd: number;
  live_unavailable_reason?: "no_key" | "budget_spent" | null;
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
        llm: "nebius" | "scripted";
        backend: string;
        models: Record<string, string>;
        max_universes: number;
      }
    >
  | EventBase<"stage", { name: StageName; status: "started" | "done"; detail: string }>
  | EventBase<"plan.ready", { plan: AnalysisPlan }>
  | EventBase<
      "option.coded",
      { step_id: string; option_id: string; ok: boolean; attempts: number; error: string | null }
    >
  | EventBase<"option.proposed", { step_id: string; option: Option }>
  | EventBase<
      "option.judged",
      { step_id: string; option_id: string; defensibility: number; accepted: boolean; reason: string }
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
  | EventBase<"run.finished", { status: "completed" | "failed"; elapsed_s: number }>
  | EventBase<"run.failed", { error: string }>;

export type RunEventType = RunEvent["type"];
