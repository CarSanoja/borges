import { describe, expect, it } from "vitest";
import { countSpans, formatCostUsd, formatDuration, kindLabel, shortHash } from "./spanFormat";
import { sampleTrace } from "./traceFixture";

describe("spanFormat", () => {
  it("formats durations across magnitudes", () => {
    expect(formatDuration(null)).toBe("running");
    expect(formatDuration(0.2)).toBe("<1 ms");
    expect(formatDuration(450.4)).toBe("450 ms");
    expect(formatDuration(1840)).toBe("1.8 s");
    expect(formatDuration(125_000)).toBe("2 min 5 s");
  });

  it("shortens hashes and formats cost", () => {
    expect(shortHash("0123456789abcdef0123")).toBe("01234567…0123");
    expect(shortHash("abc")).toBe("abc");
    expect(formatCostUsd(0)).toBe("$0");
    expect(formatCostUsd(0.0009)).toBe("$0.00090");
    expect(formatCostUsd(0.5)).toBe("$0.500");
  });

  it("labels kinds and counts spans", () => {
    expect(kindLabel("model_call")).toBe("Model");
    expect(kindLabel(null)).toBe("Span");
    expect(countSpans(sampleTrace().roots)).toBe(5);
  });
});
