import type { RunEvent, RunEventType } from "../types/contracts";

interface Frame {
  type: string;
  data: string;
}

export function parseFrames(buffer: string): { frames: Frame[]; rest: string } {
  const parts = buffer.replace(/\r\n/g, "\n").split("\n\n");
  const rest = parts.pop() ?? "";
  const frames: Frame[] = [];
  for (const part of parts) {
    let type = "message";
    const data: string[] = [];
    for (const line of part.split("\n")) {
      if (line.startsWith("event:")) type = line.slice(6).trim();
      else if (line.startsWith("data:")) data.push(line.slice(5).replace(/^ /, ""));
    }
    if (data.length > 0) frames.push({ type, data: data.join("\n") });
  }
  return { frames, rest };
}

export function streamWithHeaders(
  url: string,
  headers: Record<string, string>,
  known: ReadonlySet<string>,
  terminal: ReadonlySet<RunEventType>,
  onEvent: (event: RunEvent) => void,
  onError?: (error: Event) => void,
): () => void {
  const controller = new AbortController();
  let finished = false;
  const run = async () => {
    const response = await fetch(url, { headers: { ...headers, Accept: "text/event-stream" }, signal: controller.signal });
    if (!response.ok || !response.body) throw new Error(String(response.status));
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    for (;;) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const parsed = parseFrames(buffer);
      buffer = parsed.rest;
      for (const frame of parsed.frames) {
        if (!known.has(frame.type)) continue;
        try {
          onEvent(JSON.parse(frame.data) as RunEvent);
        } catch {
          continue;
        }
        if (terminal.has(frame.type as RunEventType)) {
          finished = true;
          controller.abort();
          return;
        }
      }
    }
    if (!finished) throw new Error("closed");
  };
  run().catch(() => {
    if (!controller.signal.aborted) onError?.(new Event("error"));
  });
  return () => {
    finished = true;
    controller.abort();
  };
}
