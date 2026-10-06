import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { localDate, localDateTime, toDate } from "./localTime";

describe("local time rendering", () => {
  beforeEach(() => {
    vi.stubEnv("TZ", "America/Los_Angeles");
  });

  afterEach(() => {
    vi.unstubAllEnvs();
  });

  it("shows the viewer's calendar day, not the UTC day, for a west-of-UTC viewer", () => {
    const earlyUtc = Date.UTC(2026, 9, 7, 3, 0, 0) / 1000;
    expect(new Date(earlyUtc * 1000).toISOString().slice(0, 10)).toBe("2026-10-07");
    expect(localDate(earlyUtc)).toBe("2026-10-06");
  });

  it("accepts epoch seconds and ISO strings and renders local clock time", () => {
    const iso = "2026-10-07T03:15:09.123456+00:00";
    expect(localDateTime(iso)).toMatch(/^2026-10-06 20:15:09 /);
    expect(localDateTime(Date.parse(iso) / 1000)).toMatch(/^2026-10-06 20:15:09 /);
  });

  it("returns null for missing or unparseable stamps", () => {
    expect(toDate(null)).toBeNull();
    expect(toDate("not a date")).toBeNull();
    expect(localDateTime(undefined)).toBeNull();
  });
});
