import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { buildSampleRun } from "../../fixtures/sampleRun";
import { foldEvents } from "../run/reducer";
import { Telemetry } from "./Telemetry";
import { formatCost, formatTokens } from "./telemetryFormat";

const events = buildSampleRun("t");

describe("Telemetry", () => {
  it("shows usage counters with the cached count and cost", () => {
    const base = foldEvents("t", events);
    const snapshot = {
      ...base,
      llm: "nebius" as const,
      usage: { tokens_in: 12000, tokens_out: 3400, cost_usd: 0.0243, llm_calls: 14, cached_calls: 5, checkpoints: 31, universes: 8 },
    };
    render(<Telemetry snapshot={snapshot} />);
    const region = screen.getByLabelText("Telemetry");
    expect(region).toHaveTextContent("8 universes");
    expect(region).toHaveTextContent("31 sandbox checkpoints");
    expect(region).toHaveTextContent("14 LLM calls");
    expect(region).toHaveTextContent("5 cached");
    expect(region).toHaveTextContent("15.4k tokens");
    expect(region).toHaveTextContent("$0.0243 USD");
  });

  it("says scripted instead of showing token counts for a scripted run", () => {
    const snapshot = foldEvents("t", events);
    expect(snapshot.llm).toBe("scripted");
    render(<Telemetry snapshot={snapshot} />);
    const region = screen.getByLabelText("Telemetry");
    expect(region).toHaveTextContent("scripted, no model calls");
    expect(region).not.toHaveTextContent("tokens");
    expect(region).not.toHaveTextContent("LLM calls");
  });

  it("marks stages done, active and pending", () => {
    const cut = events.findIndex((e) => e.type === "stage" && e.data.name === "single_flips" && e.data.status === "started");
    const snapshot = foldEvents("t", events.slice(0, cut + 1));
    render(<Telemetry snapshot={snapshot} />);
    const stage = (label: string) => screen.getByText(label).closest("li");
    expect(stage("Profiling")).toHaveAttribute("data-state", "done");
    expect(stage("Single flips")).toHaveAttribute("data-state", "active");
    expect(stage("Narrating")).toHaveAttribute("data-state", "pending");
  });

  it("formats tokens and cost", () => {
    expect(formatTokens(950)).toBe("950");
    expect(formatTokens(2_500_000)).toBe("2.50M");
    expect(formatCost(1.5)).toBe("$1.50");
  });
});

describe("Telemetry coding summary", () => {
  it("states how many options were smoke tested and repaired, and is silent for old recordings", () => {
    const base = foldEvents("t", events);
    const report = base.report!;
    const withCoding = {
      ...base,
      report: { ...report, coding: { options: 9, smoke_tested: 8, repaired_after_smoke: 2, failed: 0 } },
    };
    const { rerender } = render(<Telemetry snapshot={withCoding} />);
    expect(screen.getByLabelText("Telemetry")).toHaveTextContent("8 options tested on a sample, 2 repaired after a failing test");
    rerender(<Telemetry snapshot={{ ...base, report: { ...report, coding: undefined } }} />);
    expect(screen.getByLabelText("Telemetry")).not.toHaveTextContent("tested on a sample");
  });

  it("reports options dropped by the defensibility judge", () => {
    const base = foldEvents("t", events);
    const coding = { options: 9, smoke_tested: 8, repaired_after_smoke: 0, failed: 0, options_dropped_by_judge: 2 };
    render(<Telemetry snapshot={{ ...base, report: { ...base.report!, coding } }} />);
    expect(screen.getByLabelText("Telemetry")).toHaveTextContent("2 dropped by the defensibility judge");
  });

  it("reports options dropped by Armor", () => {
    const base = foldEvents("t", events);
    const coding = { options: 9, smoke_tested: 8, repaired_after_smoke: 0, failed: 0, options_dropped_by_armor: 1 };
    render(<Telemetry snapshot={{ ...base, report: { ...base.report!, coding } }} />);
    expect(screen.getByLabelText("Telemetry")).toHaveTextContent("1 dropped by Armor as tool poisoning");
  });

  it("pluralises the counters", () => {
    const base = foldEvents("t", events);
    const snapshot = {
      ...base,
      llm: "nebius" as const,
      usage: { tokens_in: 1, tokens_out: 1, cost_usd: 0, llm_calls: 1, cached_calls: 0, checkpoints: 1, universes: 1 },
    };
    render(<Telemetry snapshot={snapshot} />);
    const region = screen.getByLabelText("Telemetry");
    expect(region).toHaveTextContent("1 universe");
    expect(region).not.toHaveTextContent("1 universes");
    expect(region).toHaveTextContent("1 sandbox checkpoint");
    expect(region).not.toHaveTextContent("1 sandbox checkpoints");
    expect(region).toHaveTextContent("1 LLM call");
    expect(region).not.toHaveTextContent("1 LLM calls");
  });
});
