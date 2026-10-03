import { describe, expect, it } from "vitest";
import { placeThresholdLabel, type Marker } from "./thresholdLabel";

const TEXT = "decision threshold 0";

describe("placeThresholdLabel", () => {
  it("sits at the left under the line when nothing is near it", () => {
    const spot = placeThresholdLabel([], 100, TEXT, 150, 700);
    expect(spot).toEqual({ x: 156, y: 114, anchor: "start" });
  });

  it("moves away from markers that sit on the left of the line", () => {
    const markers: Marker[] = [{ x: 200, yTop: 95, yBottom: 118 }];
    const spot = placeThresholdLabel(markers, 100, TEXT, 150, 700);
    expect(spot).not.toBeNull();
    const width = TEXT.length * 6.8;
    const x0 = spot!.anchor === "start" ? spot!.x : spot!.x - width;
    const overlaps = x0 <= 208 && x0 + width >= 192 && spot!.y + 3 >= 87 && spot!.y - 12 <= 126;
    expect(overlaps).toBe(false);
  });

  it("never returns a spot that overlaps any marker", () => {
    const markers: Marker[] = Array.from({ length: 12 }, (_, i) => ({ x: 170 + i * 45, yTop: 90, yBottom: 112 }));
    const spot = placeThresholdLabel(markers, 100, TEXT, 150, 700);
    if (spot === null) return;
    const width = TEXT.length * 6.8;
    const x0 = spot.anchor === "start" ? spot.x : spot.x - width;
    for (const m of markers) {
      const hit = m.x + 8 >= x0 && m.x - 8 <= x0 + width && m.yBottom + 8 >= spot.y - 12 && m.yTop - 8 <= spot.y + 3;
      expect(hit).toBe(false);
    }
  });

  it("returns null when markers cover every position so the caller can fall back", () => {
    const markers: Marker[] = Array.from({ length: 60 }, (_, i) => ({ x: 150 + i * 10, yTop: 60, yBottom: 140 }));
    expect(placeThresholdLabel(markers, 100, TEXT, 150, 700)).toBeNull();
  });
});
