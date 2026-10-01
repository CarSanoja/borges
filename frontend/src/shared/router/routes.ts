export type Route =
  | { name: "landing" }
  | { name: "run"; runId: string }
  | { name: "replay"; caseId: string }
  | { name: "not_found" };

export interface Location {
  route: Route;
  mock: boolean;
}

export function parseLocation(pathname: string, search: string): Location {
  const mock = new URLSearchParams(search).get("mock") === "1";
  const parts = pathname.split("/").filter(Boolean).map(decodeURIComponent);
  if (parts.length === 0) return { route: { name: "landing" }, mock };
  const [head, id] = parts;
  if (parts.length === 2 && id) {
    if (head === "run") return { route: { name: "run", runId: id }, mock };
    if (head === "replay") return { route: { name: "replay", caseId: id }, mock };
  }
  return { route: { name: "not_found" }, mock };
}

export function runPath(runId: string): string {
  return `/run/${encodeURIComponent(runId)}`;
}

export function replayPath(caseId: string): string {
  return `/replay/${encodeURIComponent(caseId)}`;
}

export function withMock(path: string): string {
  return `${path}?mock=1`;
}
