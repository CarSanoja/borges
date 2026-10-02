import { afterEach, describe, expect, it } from "vitest";
import { authHeaders, clearApiKey, readApiKey, storeApiKey } from "./apiKey";

describe("api key storage", () => {
  afterEach(() => window.sessionStorage.clear());

  it("sends nothing without a key", () => {
    expect(readApiKey()).toBeNull();
    expect(authHeaders()).toEqual({});
  });

  it("keeps a trimmed key in sessionStorage and sends it as a bearer token", () => {
    storeApiKey("  bk_abc_def ");
    expect(window.sessionStorage.getItem("borges.apiKey")).toBe("bk_abc_def");
    expect(window.localStorage.getItem("borges.apiKey")).toBeNull();
    expect(authHeaders()).toEqual({ Authorization: "Bearer bk_abc_def" });
  });

  it("forgets the key", () => {
    storeApiKey("bk_abc_def");
    clearApiKey();
    expect(authHeaders()).toEqual({});
  });
});
