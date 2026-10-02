import type { RecordingSource } from "../types/contracts";

export type Route =
  | { name: "landing" }
  | { name: "run"; runId: string }
  | { name: "trace"; runId: string }
  | { name: "replay"; caseId: string; source: RecordingSource | null }
  | { name: "not_found" };

export interface Location {
  route: Route;
  mock: boolean;
}

export function parseLocation(pathname: string, search: string): Location {
  const params = new URLSearchParams(search);
  const mock = params.get("mock") === "1";
  const requested = params.get("source");
  const source: RecordingSource | null = requested === "live" || requested === "scripted" ? requested : null;
  const parts = pathname.split("/").filter(Boolean).map(decodeURIComponent);
  if (parts.length === 0) return { route: { name: "landing" }, mock };
  const [head, id] = parts;
  if (parts.length === 3 && id && parts[2] === "trace" && head === "run") {
    return { route: { name: "trace", runId: id }, mock };
  }
  if (parts.length === 2 && id) {
    if (head === "run") return { route: { name: "run", runId: id }, mock };
    if (head === "replay") return { route: { name: "replay", caseId: id, source }, mock };
  }
  return { route: { name: "not_found" }, mock };
}

export function runPath(runId: string): string {
  return `/run/${encodeURIComponent(runId)}`;
}

export function tracePath(runId: string): string {
  return `${runPath(runId)}/trace`;
}

export function replayPath(caseId: string, source: RecordingSource | null = null): string {
  const base = `/replay/${encodeURIComponent(caseId)}`;
  return source === "scripted" ? `${base}?source=scripted` : base;
}

export function withMock(path: string): string {
  return `${path}?mock=1`;
}
