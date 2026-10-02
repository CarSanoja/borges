import { act, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { RunPage } from "./RunPage";

class FakeEventSource {
  static instances: FakeEventSource[] = [];
  static readonly CLOSED = 2;
  readyState = 1;
  onerror: ((event: Event) => void) | null = null;
  listeners = new Map<string, EventListener>();

  constructor(readonly url: string) {
    FakeEventSource.instances.push(this);
  }

  addEventListener(type: string, listener: EventListener) {
    this.listeners.set(type, listener);
  }

  removeEventListener(type: string) {
    this.listeners.delete(type);
  }

  close() {
    this.readyState = 2;
  }

  emit(type: string, data: unknown) {
    this.listeners.get(type)?.(new MessageEvent(type, { data: JSON.stringify(data) }));
  }

  drop() {
    this.readyState = 2;
    this.onerror?.(new Event("error"));
  }
}


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

describe("RunPage (live source)", () => {
  beforeEach(() => {
    FakeEventSource.instances = [];
    vi.stubGlobal("EventSource", FakeEventSource);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("renders a not-found page with links home and to the recorded runs for an unknown run", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response("Unknown run", { status: 404 })));
    render(<RunPage source={{ kind: "live", runId: "r_gone" }} onHome={() => undefined} />);
    await act(async () => {
      FakeEventSource.instances[0]?.drop();
    });
    expect(await screen.findByRole("heading", { name: "Run not found" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Back to the entrance" })).toHaveAttribute("href", "/");
    expect(screen.getByRole("link", { name: /Recorded run: New checkout A\/B test/ })).toHaveAttribute(
      "href",
      "/replay/checkout_ab",
    );
    expect(screen.queryByText("Connection to the run was lost.")).toBeNull();
    expect(screen.queryByText(/Walking the garden/)).toBeNull();
  });

  it("renders a not-found page for an unknown case replay", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response("Unknown case", { status: 404 })));
    render(<RunPage source={{ kind: "replay", caseId: "nope", speed: 1 }} onHome={() => undefined} />);
    await act(async () => {
      FakeEventSource.instances[0]?.drop();
    });
    expect(await screen.findByRole("heading", { name: "Case not found" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Back to the entrance" })).toBeInTheDocument();
    expect(screen.queryByText("Connection to the run was lost.")).toBeNull();
  });

  it("keeps the connection-lost message when the run still exists", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response("{}", { status: 200 })));
    render(<RunPage source={{ kind: "live", runId: "r1" }} onHome={() => undefined} />);
    await act(async () => {
      FakeEventSource.instances[0]?.drop();
    });
    expect(await screen.findByRole("alert")).toHaveTextContent("Connection to the run was lost.");
  });
});
