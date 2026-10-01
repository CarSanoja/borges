import { describe, expect, it } from "vitest";
import { buildSampleRun } from "../../fixtures/sampleRun";
import { applyEvent, foldEvents, initialSnapshot } from "./reducer";

const events = buildSampleRun("r1");

describe("reducer", () => {
  it("builds consistent, increasing sequence numbers", () => {
    events.forEach((event, index) => expect(event.seq).toBe(index + 1));
  });

  it("folds the sample run into a completed snapshot", () => {
    const snapshot = foldEvents("r1", events);
    expect(snapshot.status).toBe("completed");
    expect(snapshot.case_id).toBe("checkout_ab");
    expect(snapshot.checkpoints).toHaveLength(30);
    expect(Object.keys(snapshot.garden.universes)).toHaveLength(8);
    expect(snapshot.garden.baseline_id).toBe("u_baseline");
    expect(snapshot.last_seq).toBe(events.length);
    expect(snapshot.report).not.toBeNull();
    expect(snapshot.usage.universes).toBe(8);
    expect(snapshot.usage.checkpoints).toBe(30);
  });

  it("verifies the flip and reproduces it", () => {
    const flip = foldEvents("r1", events).flip;
    expect(flip?.reproduced).toBe(true);
    expect(flip?.baseline_verdict).toBe("SHIP");
    expect(flip?.flipped_verdict).toBe("DON'T SHIP");
    expect(flip?.changes[0]?.to_option).toBe("exclude_internal");
  });

  it("shares prefixes between the baseline and its forks", () => {
    const universes = foldEvents("r1", events).garden.universes;
    const base = universes["u_baseline"]!;
    const flipped = universes["u_bot_filter_min_2s"]!;
    expect(flipped.checkpoints[0]).toBe(base.checkpoints[0]);
    expect(flipped.checkpoints[1]).not.toBe(base.checkpoints[1]);
    expect(universes["u_internal_traffic_exclude_internal"]?.flipped).toBe(true);
    expect(universes["u_model_logit_platform"]?.flipped).toBe(false);
  });

  it("appends and judges adversary options", () => {
    const plan = foldEvents("r1", events).plan!;
    const bot = plan.steps.find((s) => s.id === "bot_filter")!;
    const adversary = bot.options.find((o) => o.id === "adv_min_5s");
    expect(bot.options).toHaveLength(3);
    expect(adversary?.defensibility).toBe(0.82);
  });

  it("records influences in the report", () => {
    const report = foldEvents("r1", events).report!;
    expect(report.influences[0]?.step_id).toBe("internal_traffic");
    expect(report.n_universes).toBe(7);
    expect(report.n_flipped).toBe(1);
  });

  it("keeps last_seq as the max seq and handles failure", () => {
    const started = events[0]!;
    const late = applyEvent(initialSnapshot("r1"), { ...started, seq: 9 });
    const early = applyEvent(late, { ...started, seq: 3 });
    expect(early.last_seq).toBe(9);
    const failed = applyEvent(early, {
      seq: 10,
      ts: 1,
      run_id: "r1",
      type: "run.failed",
      data: { error: "boom" },
    });
    expect(failed.status).toBe("failed");
    expect(failed.error).toBe("boom");
  });

  it("does not mutate the previous snapshot", () => {
    const before = initialSnapshot("r1");
    applyEvent(before, events[0]!);
    expect(before.title).toBe("");
  });
});
