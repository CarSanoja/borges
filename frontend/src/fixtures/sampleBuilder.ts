import type { RunEvent, RunEventType, UsageSnapshot } from "../shared/types/contracts";

type DataOf<T extends RunEventType> = Extract<RunEvent, { type: T }>["data"];

export class EventLog {
  readonly events: RunEvent[] = [];
  private seq = 0;
  private clock = 0;

  constructor(private readonly runId: string) {}

  emit<T extends RunEventType>(type: T, data: DataOf<T>, dt = 0.25): void {
    this.seq += 1;
    this.clock = Number((this.clock + dt).toFixed(3));
    this.events.push({ seq: this.seq, ts: this.clock, run_id: this.runId, type, data } as RunEvent);
  }

  get elapsed(): number {
    return this.clock;
  }
}

export class UsageMeter {
  private state: UsageSnapshot = {
    tokens_in: 0,
    tokens_out: 0,
    cost_usd: 0,
    llm_calls: 0,
    cached_calls: 0,
    checkpoints: 0,
    universes: 0,
  };

  constructor(private readonly log: EventLog) {}

  add(delta: Partial<UsageSnapshot>, dt = 0.05): void {
    const next = { ...this.state };
    for (const key of Object.keys(delta) as (keyof UsageSnapshot)[]) {
      next[key] += delta[key] ?? 0;
    }
    next.cost_usd = Number(next.cost_usd.toFixed(5));
    this.state = next;
    this.log.emit("usage", { ...next }, dt);
  }
}
