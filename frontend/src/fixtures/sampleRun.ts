import type { Change, Flip, Report, RunEvent, StageName, Step } from "../shared/types/contracts";
import { EventLog, UsageMeter } from "./sampleBuilder";
import { GardenBuilder } from "./sampleGarden";
import { ADVERSARY_OPTION, SAMPLE_QUESTION, SAMPLE_RULE, samplePlan } from "./samplePlan";
import { buildReport } from "./sampleReport";

export const SAMPLE_RUN_ID = "sample-checkout";

export function buildSampleRun(runId: string = SAMPLE_RUN_ID): RunEvent[] {
  const log = new EventLog(runId);
  const meter = new UsageMeter(log);
  const plan = samplePlan();
  const stage = (name: StageName, status: "started" | "done", detail: string, dt = 0.4) =>
    log.emit("stage", { name, status, detail }, dt);

  log.emit("run.started", {
    case_id: "checkout_ab",
    title: "Checkout redesign A/B",
    question: SAMPLE_QUESTION,
    decision_rule: SAMPLE_RULE,
    mode: "replay",
    llm: "scripted",
    backend: "local",
    models: { planner: "nemotron-3-super", coder: "nemotron-3-nano", narrator: "nemotron-3-ultra" },
    max_universes: 24,
  });
  stage("profiling", "started", "Reading 48,210 rows");
  stage("profiling", "done", "6 columns profiled", 0.6);
  stage("planning", "started", "Planner drafts the analysis");
  meter.add({ llm_calls: 1, tokens_in: 3120, tokens_out: 1480, cost_usd: 0.0041 }, 0.7);
  log.emit("plan.ready", { plan }, 0.2);
  stage("planning", "done", "5 steps, 10 options", 0.2);

  stage("coding", "started", "Writing code for every option");
  for (const step of plan.steps) {
    for (const option of step.options) {
      log.emit("option.coded", { step_id: step.id, option_id: option.id, ok: true, attempts: 1, error: null }, 0.12);
      meter.add({ llm_calls: 1, tokens_in: 910, tokens_out: 380, cost_usd: 0.0006 }, 0.02);
    }
  }
  stage("coding", "done", "10 options compiled", 0.2);

  const garden = new GardenBuilder(log, meter, plan.steps, SAMPLE_RULE);
  stage("baseline", "started", "Walking the default path");
  garden.root();
  const defaults = garden.defaults();
  const baseline = garden.run({ id: "u_baseline", kind: "baseline", choices: defaults, changed: [] });
  stage("baseline", "done", `${baseline.verdict}`, 0.3);

  stage("single_flips", "started", "Forking one decision at a time");
  let flip: Flip | null = null;
  for (const step of plan.steps) {
    for (const option of step.options.filter((o) => !o.is_default)) {
      const universe = garden.run(singleSpec(step, option.id, defaults));
      if (universe.flipped && !flip) {
        flip = makeFlip(universe.id, step, option.id, baseline.result!, universe.result!, baseline.verdict!, universe.verdict!);
        log.emit("flip.found", { flip }, 0.5);
      }
    }
  }
  stage("single_flips", "done", "5 forks explored", 0.3);

  stage("adversary", "started", "An adversary hunts for another way to reverse it");
  meter.add({ llm_calls: 1, tokens_in: 5200, tokens_out: 900, cost_usd: 0.0074 }, 0.9);
  log.emit("option.proposed", { step_id: "bot_filter", option: ADVERSARY_OPTION }, 0.3);
  log.emit("option.judged", { step_id: "bot_filter", option_id: ADVERSARY_OPTION.id, defensibility: 0.82, accepted: true, reason: "A second bot mode is visible in the duration histogram." }, 0.6);
  meter.add({ llm_calls: 1, tokens_in: 2100, tokens_out: 260, cost_usd: 0.0032 }, 0.02);
  const advStep = plan.steps.find((s) => s.id === "bot_filter")!;
  garden.run(singleSpec(advStep, ADVERSARY_OPTION.id, defaults, "adversary"));
  stage("adversary", "done", "1 option accepted, 0 flips", 0.3);

  stage("verifying", "started", "Re-executing the flip from scratch");
  const flipped = flip!;
  const verification = garden.run({
    id: "u_verify",
    kind: "verification",
    choices: { ...defaults, internal_traffic: "exclude_internal" },
    changed: ["internal_traffic"],
    fresh: true,
  });
  const reproduced = verification.result?.estimate === flipped.flipped_result.estimate;
  const verified: Flip = { ...flipped, reproduced, reproduce_command: "borges reproduce sample-checkout u_internal_traffic_exclude_internal" };
  log.emit("flip.verified", { flip: verified }, 0.4);
  stage("verifying", "done", reproduced ? "Reproduced exactly" : "Mismatch", 0.2);

  stage("narrating", "started", "Writing the fragility report");
  meter.add({ llm_calls: 1, tokens_in: 9800, tokens_out: 1100, cost_usd: 0.0142 }, 1.1);
  const report: Report = buildReport(plan, garden, verified);
  log.emit("report.ready", { report }, 0.3);
  stage("narrating", "done", "Report ready", 0.2);
  log.emit("run.finished", { status: "completed", elapsed_s: log.elapsed }, 0.2);
  return log.events;
}

function singleSpec(step: Step, optionId: string, defaults: Record<string, string>, kind: "single" | "adversary" = "single") {
  return {
    id: `u_${step.id}_${optionId}`,
    kind,
    choices: { ...defaults, [step.id]: optionId },
    changed: [step.id],
  };
}

function makeFlip(
  universeId: string,
  step: Step,
  optionId: string,
  baselineResult: Flip["baseline_result"],
  flippedResult: Flip["flipped_result"],
  baselineVerdict: string,
  flippedVerdict: string,
): Flip {
  const option = step.options.find((o) => o.id === optionId)!;
  const from = step.options.find((o) => o.is_default)!;
  const change: Change = {
    step_id: step.id,
    step_title: step.title,
    from_option: from.id,
    to_option: option.id,
    to_label: option.label,
    rationale: option.rationale,
    source: null,
    defensibility: option.defensibility,
  };
  return {
    universe_id: universeId,
    changes: [change],
    baseline_result: baselineResult,
    flipped_result: flippedResult,
    baseline_verdict: baselineVerdict,
    flipped_verdict: flippedVerdict,
    reproduced: null,
    reproduce_command: null,
  };
}
