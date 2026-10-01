import { describe, expect, it } from "vitest";
import { parseLocation, replayPath, runPath, withMock } from "./routes";

describe("parseLocation", () => {
  it("matches the landing route", () => {
    expect(parseLocation("/", "")).toEqual({ route: { name: "landing" }, mock: false });
  });

  it("matches run and replay routes", () => {
    expect(parseLocation("/run/abc123", "").route).toEqual({ name: "run", runId: "abc123" });
    expect(parseLocation("/replay/checkout_ab", "").route).toEqual({ name: "replay", caseId: "checkout_ab" });
  });

  it("detects mock mode", () => {
    expect(parseLocation("/run/sample", "?mock=1").mock).toBe(true);
    expect(parseLocation("/", "?mock=0").mock).toBe(false);
  });

  it("returns not_found for unknown paths", () => {
    expect(parseLocation("/nope", "").route.name).toBe("not_found");
    expect(parseLocation("/run", "").route.name).toBe("not_found");
    expect(parseLocation("/run/a/b", "").route.name).toBe("not_found");
  });

  it("round-trips encoded ids", () => {
    const path = runPath("a b/c");
    expect(parseLocation(path, "").route).toEqual({ name: "run", runId: "a b/c" });
    expect(replayPath("x")).toBe("/replay/x");
    expect(withMock("/run/x")).toBe("/run/x?mock=1");
  });
});
