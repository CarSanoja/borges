import { act, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { App } from "./App";
import { buildSampleRun } from "./fixtures/sampleRun";
import { foldEvents } from "./features/run/reducer";

describe("App mock run end to end", () => {
  beforeEach(() => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("offline")));
    window.history.pushState({}, "", "/run/sample?mock=1");
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.unstubAllGlobals();
    window.history.pushState({}, "", "/");
  });

  it("grows the garden, flips the verdict, plots every universe and opens the drawer", async () => {
    const final = foldEvents("sample", buildSampleRun("sample"));
    const universes = Object.values(final.garden.universes);
    render(<App />);
    await act(async () => {
      await vi.advanceTimersByTimeAsync(60_000);
    });
    await act(async () => {
      await vi.advanceTimersByTimeAsync(2_000);
    });

    expect(screen.getByRole("status")).toHaveTextContent("Complete");
    expect(screen.getAllByTestId("garden-node")).toHaveLength(final.checkpoints.length);

    const verdict = screen.getByLabelText("Verdict");
    expect(verdict).toHaveAttribute("data-state", "flipped");
    expect(within(verdict).getByText("Reproduced from scratch")).toBeInTheDocument();

    const curve = screen.getByLabelText("Estimates by universe");
    const finished = universes.filter((u) => u.status === "done" && u.result !== null && u.kind !== "verification").length;
    expect(within(curve).getAllByRole("button")).toHaveLength(finished);

    const leaves = screen
      .getAllByTestId("garden-node")
      .filter((node) => node.getAttribute("data-leaf") === "true");
    expect(leaves).toHaveLength(universes.length);
    await userEvent.click(leaves[0] as HTMLElement);
    expect(screen.getByLabelText("Universe")).toBeInTheDocument();
  });
});
