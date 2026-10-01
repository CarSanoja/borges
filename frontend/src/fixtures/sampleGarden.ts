import type { DecisionRule, Step, StepTrace, Universe, UniverseKind } from "../shared/types/contracts";
import type { EventLog, UsageMeter } from "./sampleBuilder";
import { BASE_ROWS, ROW_FACTORS, resultFor, verdictOf } from "./sampleResults";

export const ROOT_ID = "ck_root";

interface UniverseSpec {
  id: string;
  kind: UniverseKind;
  choices: Record<string, string>;
  changed: string[];
  fresh?: boolean;
}

export class GardenBuilder {
  private readonly cache = new Map<string, string>();
  private checkpointCount = 0;
  readonly finished = new Map<string, Universe>();

  constructor(
    private readonly log: EventLog,
    private readonly meter: UsageMeter,
    private readonly steps: Step[],
    private readonly rule: DecisionRule,
  ) {}

  defaults(): Record<string, string> {
    const choices: Record<string, string> = {};
    for (const step of this.steps) {
      choices[step.id] = step.options.find((o) => o.is_default)?.id ?? "";
    }
    return choices;
  }

  root(): void {
    this.cache.set("", ROOT_ID);
    this.log.emit(
      "checkpoint.created",
      { checkpoint_id: ROOT_ID, parent_id: null, step_id: null, option_id: null, depth: 0, duration_s: 0.8 },
      0.4,
    );
    this.meter.add({ checkpoints: 1 });
  }

  run(spec: UniverseSpec): Universe {
    const started = this.shell(spec);
    this.log.emit("universe.started", { universe: started }, 0.2);
    const checkpoints: string[] = [];
    const traces: StepTrace[] = [];
    let parent = ROOT_ID;
    let rows = BASE_ROWS;
    let prefix = spec.fresh ? "#fresh" : "";
    this.steps.forEach((step, index) => {
      const optionId = spec.choices[step.id] ?? "";
      prefix += `/${step.id}=${optionId}`;
      const after = Math.round(rows * (ROW_FACTORS[optionId] ?? 1));
      traces.push({ step_id: step.id, option_id: optionId, rows_before: rows, rows_after: after, note: traceNote(rows, after) });
      rows = after;
      let id = this.cache.get(prefix);
      if (!id) {
        this.checkpointCount += 1;
        id = `ck_${String(this.checkpointCount).padStart(2, "0")}${optionId.slice(0, 3)}`;
        this.cache.set(prefix, id);
        this.log.emit(
          "checkpoint.created",
          { checkpoint_id: id, parent_id: parent, step_id: step.id, option_id: optionId, depth: index + 1, duration_s: 1.1 },
          0.18,
        );
        this.meter.add({ checkpoints: 1 }, 0.02);
      }
      checkpoints.push(id);
      parent = id;
    });
    const changedOption = spec.changed.length ? (spec.choices[spec.changed[0] ?? ""] ?? null) : null;
    const result = resultFor(changedOption, rows, this.rule);
    const verdict = verdictOf(result, this.rule);
    const baseline = this.finished.get("u_baseline");
    const done: Universe = {
      ...started,
      status: "done",
      result,
      verdict,
      flipped: baseline ? verdict !== baseline.verdict : null,
      checkpoints,
      traces,
      duration_s: Number((checkpoints.length * 1.1).toFixed(1)),
    };
    this.log.emit("universe.finished", { universe: done }, 0.3);
    this.meter.add({ universes: 1 }, 0.02);
    this.finished.set(spec.id, done);
    return done;
  }

  private shell(spec: UniverseSpec): Universe {
    return {
      id: spec.id,
      choices: spec.choices,
      changed: spec.changed,
      kind: spec.kind,
      status: "running",
      result: null,
      verdict: null,
      flipped: null,
      checkpoints: [],
      traces: [],
      error: null,
      duration_s: 0,
    };
  }
}

function traceNote(before: number, after: number): string {
  if (before === after) return "No rows removed";
  return `Removed ${(before - after).toLocaleString("en-US")} rows`;
}
