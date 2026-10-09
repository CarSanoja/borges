import { afterEach, describe, expect, it, vi } from "vitest";
import { buildSampleRun } from "../../fixtures/sampleRun";
import { storeApiKey } from "./apiKey";
import { parseFrames } from "./fetchStream";
import { subscribeEvents } from "./sse";

function sseResponse(chunks: string[]): Response {
  const encoder = new TextEncoder();
  const body = new ReadableStream<Uint8Array>({
    start(controller) {
      for (const chunk of chunks) controller.enqueue(encoder.encode(chunk));
      controller.close();
    },
  });
  return new Response(body, { status: 200, headers: { "Content-Type": "text/event-stream" } });
}

async function settle() {
  for (let i = 0; i < 10; i += 1) await new Promise((resolve) => setTimeout(resolve, 0));
}

describe("keyed event stream", () => {
  afterEach(() => {
    window.sessionStorage.clear();
    vi.unstubAllGlobals();
  });

  it("parses frames split across chunks and CRLF", () => {
    const first = parseFrames("event: usage\r\ndata: {\"a\":1}\r\n\r\nevent: sta");
    expect(first.frames).toEqual([{ type: "usage", data: '{"a":1}' }]);
    expect(first.rest).toBe("event: sta");
  });

  it("follows a keyed run with the bearer header and never puts the key in the url", async () => {
    storeApiKey("bk_secret");
    const event = buildSampleRun("r")[0]!;
    const fetchMock = vi.fn().mockResolvedValue(sseResponse([`event: ${event.type}\ndata: ${JSON.stringify(event)}\n\n`]));
    vi.stubGlobal("fetch", fetchMock);
    vi.stubGlobal("EventSource", vi.fn());
    const onEvent = vi.fn();
    subscribeEvents("/api/runs/r/events?from_seq=0", onEvent);
    await settle();
    expect(EventSource).not.toHaveBeenCalled();
    const [url, init] = fetchMock.mock.calls[0]!;
    expect(url).not.toContain("bk_secret");
    expect(init.headers.Authorization).toBe("Bearer bk_secret");
    expect(onEvent).toHaveBeenCalledWith(event);
  });

  it("reports an error when the keyed stream is refused", async () => {
    storeApiKey("bk_secret");
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response("Unknown run", { status: 404 })));
    const onError = vi.fn();
    subscribeEvents("/api/runs/r/events?from_seq=0", vi.fn(), onError);
    await settle();
    expect(onError).toHaveBeenCalledOnce();
  });
});
