import { act, renderHook } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { navigate, useLocation } from "./useLocation";

describe("useLocation", () => {
  it("reacts to navigate and popstate", () => {
    window.history.replaceState(null, "", "/");
    const { result } = renderHook(() => useLocation());
    expect(result.current.route.name).toBe("landing");
    act(() => navigate("/run/r9?mock=1"));
    expect(result.current.route).toEqual({ name: "run", runId: "r9" });
    expect(result.current.mock).toBe(true);
    act(() => {
      window.history.pushState(null, "", "/replay/c1");
      window.dispatchEvent(new PopStateEvent("popstate"));
    });
    expect(result.current.route).toEqual({ name: "replay", caseId: "c1", source: null });
  });
});
