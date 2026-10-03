export interface Marker {
  x: number;
  yTop: number;
  yBottom: number;
}

export interface LabelSpot {
  x: number;
  y: number;
  anchor: "start" | "end";
}

const GLYPH_WIDTH = 6.8;
const LABEL_RISE = 12;
const LABEL_DROP = 3;
const PAD = 8;

export function labelWidth(text: string): number {
  return text.length * GLYPH_WIDTH;
}

function collides(markers: readonly Marker[], x0: number, x1: number, y0: number, y1: number): boolean {
  return markers.some((m) => m.x + PAD >= x0 && m.x - PAD <= x1 && m.yBottom + PAD >= y0 && m.yTop - PAD <= y1);
}

export function placeThresholdLabel(
  markers: readonly Marker[],
  thresholdY: number,
  text: string,
  left: number,
  right: number,
): LabelSpot | null {
  const width = labelWidth(text);
  const baselines = [thresholdY + 14, thresholdY - 6];
  const starts: Array<{ anchor: "start" | "end"; x: number }> = [
    { anchor: "start", x: left + 6 },
    { anchor: "end", x: right - 6 },
  ];
  for (const baseline of baselines) {
    for (const start of starts) {
      const x0 = start.anchor === "start" ? start.x : start.x - width;
      if (!collides(markers, x0, x0 + width, baseline - LABEL_RISE, baseline + LABEL_DROP)) {
        return { x: start.x, y: baseline, anchor: start.anchor };
      }
    }
    const span = right - left - 12;
    for (let x0 = left + 6; x0 + width <= left + 6 + span; x0 += 12) {
      if (!collides(markers, x0, x0 + width, baseline - LABEL_RISE, baseline + LABEL_DROP)) {
        return { x: x0, y: baseline, anchor: "start" };
      }
    }
  }
  return null;
}
