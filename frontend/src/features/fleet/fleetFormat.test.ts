import { describe, expect, it } from "vitest";
import { approvalLabel, formatPublished, shortSha } from "./fleetFormat";

describe("fleetFormat", () => {
  it("shortens shas and handles null", () => {
    expect(shortSha("abcdef0123456789")).toBe("abcdef0123");
    expect(shortSha(null)).toBe("none");
  });

  it("labels approval states", () => {
    expect(approvalLabel("approved")).toBe("approved");
    expect(approvalLabel("unpublished")).toBe("unpublished change");
  });

  it("formats the publish time in UTC", () => {
    expect(formatPublished(0)).toBe("1970-01-01 00:00 UTC");
  });
});
