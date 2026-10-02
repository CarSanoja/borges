import { describe, expect, it } from "vitest";
import { sampleSummary, sampleUsed } from "./memoryFixture";
import { modeText, reusedSummary, reusedTotal, shortFingerprint, totalCount } from "./memoryFormat";

describe("memoryFormat", () => {
  it("totals what a run reused", () => {
    expect(reusedTotal(sampleUsed())).toBe(18);
    expect(reusedTotal(null)).toBe(0);
    expect(reusedSummary(sampleUsed({ reused: { code: 2 } }))).toBe("2 validated code");
  });

  it("says plainly when the public memory is unencrypted", () => {
    expect(modeText(sampleSummary())).toContain("stored unencrypted");
    expect(modeText(sampleSummary({ encrypted: true }))).toContain("encrypted at rest");
  });

  it("explains why memory is off", () => {
    const off = sampleSummary({ enabled: false, mode: "keyed", note: "no key" });
    expect(modeText(off)).toBe("Memory is off for you: no key");
  });

  it("describes private memory and shortens fingerprints", () => {
    expect(modeText(sampleSummary({ mode: "keyed", encrypted: true }))).toContain("visible only to your key");
    expect(totalCount(sampleSummary())).toBe(19);
    expect(shortFingerprint("abcdefghijklmnop")).toBe("abcdefghijkl");
  });
});
