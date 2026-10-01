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
