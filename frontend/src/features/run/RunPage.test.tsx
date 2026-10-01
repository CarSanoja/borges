import { act, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { buildSampleRun } from "../../fixtures/sampleRun";
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

const GONE = /This run no longer exists on this server/;


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

  it("explains an unknown run instead of a lost connection", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response("Unknown run", { status: 404 })));
    render(<RunPage source={{ kind: "live", runId: "r_gone" }} onHome={() => undefined} />);
    await act(async () => {
      FakeEventSource.instances[0]?.drop();
    });
    expect(await screen.findByRole("alert")).toHaveTextContent(GONE);
    expect(screen.queryByText("Connection to the run was lost.")).toBeNull();
  });

  it("links to the case replay when the case is known", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response("Unknown run", { status: 404 })));
    const onOpenReplay = vi.fn();
    render(<RunPage source={{ kind: "live", runId: "r1" }} onHome={() => undefined} onOpenReplay={onOpenReplay} />);
    const started = buildSampleRun("r1")[0];
    await act(async () => {
      FakeEventSource.instances[0]?.emit("run.started", started);
      FakeEventSource.instances[0]?.drop();
    });
    await userEvent.click(await screen.findByRole("button", { name: "Watch the recorded run" }));
    expect(onOpenReplay).toHaveBeenCalledWith("checkout_ab");
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
