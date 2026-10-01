import type {
  AnalysisPlan,
  RunEvent,
  RunSnapshot,
  Step,
  Universe,
  UsageSnapshot,
} from "../../shared/types/contracts";

export const EMPTY_USAGE: UsageSnapshot = {
  tokens_in: 0,
  tokens_out: 0,
  cost_usd: 0,
  llm_calls: 0,
  cached_calls: 0,
  checkpoints: 0,
  universes: 0,
};

export function initialSnapshot(runId: string): RunSnapshot {
  return {
    run_id: runId,
    status: "running",
    case_id: null,
    title: "",
    question: "",
    decision_rule: null,
    stages: {},
    plan: null,
    checkpoints: [],
    garden: { baseline_id: null, universes: {} },
    flip: null,
    report: null,
    usage: EMPTY_USAGE,
    error: null,
    last_seq: 0,
  };
}

function mapSteps(plan: AnalysisPlan | null, stepId: string, fn: (step: Step) => Step): AnalysisPlan | null {
  if (!plan) return plan;
  return { ...plan, steps: plan.steps.map((step) => (step.id === stepId ? fn(step) : step)) };
}

function upsertUniverse(snapshot: RunSnapshot, universe: Universe): RunSnapshot {
  const baselineId = universe.kind === "baseline" ? universe.id : snapshot.garden.baseline_id;
  return {
    ...snapshot,
    garden: {
      baseline_id: baselineId,
      universes: { ...snapshot.garden.universes, [universe.id]: universe },
    },
  };
}

function fold(snapshot: RunSnapshot, event: RunEvent): RunSnapshot {
  switch (event.type) {
    case "run.started":
      return {
        ...snapshot,
        case_id: event.data.case_id,
        title: event.data.title,
        question: event.data.question,
        decision_rule: event.data.decision_rule,
      };
    case "stage":
      return { ...snapshot, stages: { ...snapshot.stages, [event.data.name]: event.data.status } };
    case "plan.ready":
      return { ...snapshot, plan: event.data.plan };
    case "option.proposed": {
      const { step_id, option } = event.data;
      return {
        ...snapshot,
        plan: mapSteps(snapshot.plan, step_id, (step) => ({
          ...step,
          options: [...step.options.filter((o) => o.id !== option.id), option],
        })),
      };
    }
    case "option.judged": {
      const { step_id, option_id, defensibility } = event.data;
      return {
        ...snapshot,
        plan: mapSteps(snapshot.plan, step_id, (step) => ({
          ...step,
          options: step.options.map((o) => (o.id === option_id ? { ...o, defensibility } : o)),
        })),
      };
    }
    case "checkpoint.created": {
      const { checkpoint_id, parent_id, step_id, option_id, depth } = event.data;
      if (snapshot.checkpoints.some((c) => c.checkpoint_id === checkpoint_id)) return snapshot;
      return {
        ...snapshot,
        checkpoints: [...snapshot.checkpoints, { checkpoint_id, parent_id, step_id, option_id, depth }],
      };
    }
    case "universe.started":
    case "universe.finished":
      return upsertUniverse(snapshot, event.data.universe);
    case "flip.found":
    case "flip.verified":
      return { ...snapshot, flip: event.data.flip };
    case "usage":
      return { ...snapshot, usage: event.data };
    case "report.ready":
      return { ...snapshot, report: event.data.report };
    case "run.finished":
      return { ...snapshot, status: event.data.status };
    case "run.failed":
      return { ...snapshot, status: "failed", error: event.data.error };
    case "option.coded":
      return snapshot;
  }
}

export function applyEvent(snapshot: RunSnapshot, event: RunEvent): RunSnapshot {
  const next = fold(snapshot, event);
  const lastSeq = Math.max(snapshot.last_seq, event.seq);
  return next.last_seq === lastSeq ? next : { ...next, last_seq: lastSeq };
}

export function foldEvents(runId: string, events: readonly RunEvent[]): RunSnapshot {
  return events.reduce(applyEvent, initialSnapshot(runId));
}
