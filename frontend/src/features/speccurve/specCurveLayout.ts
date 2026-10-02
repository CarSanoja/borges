import { scaleLinear, type ScaleLinear } from "d3-scale";

export interface Layout {
  width: number;
  left: number;
  right: number;
  top: number;
  curveHeight: number;
  gap: number;
  rowHeight: number;
  rows: number;
  step: number;
  height: number;
  matrixTop: number;
  y: ScaleLinear<number, number>;
}

const MIN_SLOTS = 10;

export function makeLayout(width: number, rows: number, n: number, hasReference: boolean, domain: [number, number]): Layout {
  const left = width < 640 ? 96 : 150;
  const right = hasReference ? 96 : 20;
  const top = 18;
  const curveHeight = width < 640 ? 160 : 240;
  const gap = hasReference ? 46 : 30;
  const rowHeight = 24;
  const innerWidth = Math.max(60, width - left - right);
  const step = Math.min(96, innerWidth / Math.max(n, MIN_SLOTS));
  const matrixTop = top + curveHeight + gap;
  return {
    width,
    left,
    right,
    top,
    curveHeight,
    gap,
    rowHeight,
    rows,
    step,
    matrixTop,
    height: matrixTop + rows * rowHeight + 8,
    y: scaleLinear().domain(domain).range([top + curveHeight, top]).nice(5),
  };
}

export function columnX(layout: Layout, index: number): number {
  return layout.left + (index + 0.5) * layout.step;
}
