import { describe, expect, it } from "vitest";
import css from "./tokens.css?raw";


function token(name: string): string {
  const match = css.match(new RegExp(`--${name}:\\s*(#[0-9a-fA-F]{6})`));
  if (!match?.[1]) throw new Error(`missing token ${name}`);
  return match[1];
}

function luminance(hex: string): number {
  const channels = [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16) / 255);
  const [r, g, b] = channels.map((c) => (c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4)) as [number, number, number];
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}

function ratio(a: string, b: string): number {
  const [hi, lo] = [luminance(a), luminance(b)].sort((x, y) => y - x) as [number, number];
  return (hi + 0.05) / (lo + 0.05);
}

describe("small grey text contrast", () => {
  const surfaces = ["ink-950", "ink-900", "ink-800", "ink-700"];

  it.each(["text-muted", "paper-500", "paper-300"])("%s reaches 4.5:1 on every surface", (name) => {
    for (const surface of surfaces) expect(ratio(token(name), token(surface))).toBeGreaterThanOrEqual(4.5);
  });

  it("documents why paper-700 is no longer used for text", () => {
    expect(ratio(token("paper-700"), token("ink-900"))).toBeLessThan(4.5);
  });
});
