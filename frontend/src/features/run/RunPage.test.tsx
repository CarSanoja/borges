import { act, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { RunPage } from "./RunPage";

describe("RunPage (mock source)", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("offline")));
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.unstubAllGlobals();
  });

  it("plays the mock run to completion", async () => {
    render(<RunPage source={{ kind: "mock" }} onHome={() => undefined} />);
    expect(screen.getByRole("status")).toHaveTextContent("Starting");
    await act(async () => {
      await vi.advanceTimersByTimeAsync(60_000);
    });
    expect(screen.getByRole("status")).toHaveTextContent("Complete");
    expect(screen.getByText("New checkout A/B test")).toBeInTheDocument();
    expect(screen.getByLabelText("Telemetry")).toHaveTextContent("7 universes");
  });
});
