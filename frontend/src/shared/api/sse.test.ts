import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { buildSampleRun } from "../../fixtures/sampleRun";
import { EVENT_TYPES, subscribeEvents } from "./sse";

class FakeEventSource {
  static instances: FakeEventSource[] = [];
  static readonly CLOSED = 2;
  readyState = 1;
  closed = false;
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
    this.closed = true;
    this.readyState = 2;
  }

  emit(type: string, data: string) {
    this.listeners.get(type)?.(new MessageEvent(type, { data }));
  }
}

describe("subscribeEvents", () => {
  beforeEach(() => {
    FakeEventSource.instances = [];
    vi.stubGlobal("EventSource", FakeEventSource);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("listens to every event type and parses payloads", () => {
    const onEvent = vi.fn();
    subscribeEvents("/api/x", onEvent);
    const source = FakeEventSource.instances[0]!;
    expect([...source.listeners.keys()].sort()).toEqual([...EVENT_TYPES].sort());
    const event = buildSampleRun("r")[0]!;
    source.emit(event.type, JSON.stringify(event));
    expect(onEvent).toHaveBeenCalledWith(event);
  });

  it("ignores malformed payloads", () => {
    const onEvent = vi.fn();
    subscribeEvents("/api/x", onEvent);
    FakeEventSource.instances[0]!.emit("usage", "{nope");
    expect(onEvent).not.toHaveBeenCalled();
  });

  it("closes the stream on terminal events", () => {
    subscribeEvents("/api/x", vi.fn());
    const source = FakeEventSource.instances[0]!;
    source.emit("run.finished", JSON.stringify({ seq: 1, ts: 1, run_id: "r", type: "run.finished", data: { status: "completed", elapsed_s: 1 } }));
    expect(source.closed).toBe(true);
  });

  it("reports errors only once the connection is closed", () => {
    const onError = vi.fn();
    subscribeEvents("/api/x", vi.fn(), onError);
    const source = FakeEventSource.instances[0]!;
    source.onerror?.(new Event("error"));
    expect(onError).not.toHaveBeenCalled();
    source.readyState = 2;
    source.onerror?.(new Event("error"));
    expect(onError).toHaveBeenCalledOnce();
  });

  it("returns an unsubscribe that closes the source", () => {
    const stop = subscribeEvents("/api/x", vi.fn());
    const source = FakeEventSource.instances[0]!;
    stop();
    expect(source.closed).toBe(true);
    expect(source.listeners.size).toBe(0);
  });
});
