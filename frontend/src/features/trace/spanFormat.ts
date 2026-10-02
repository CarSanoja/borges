import type { SpanAttributeValue, SpanNode } from "../../shared/types/contracts";

export function formatDuration(ms: number | null): string {
  if (ms === null) return "running";
  if (ms < 1) return "<1 ms";
  if (ms < 1000) return `${Math.round(ms)} ms`;
  if (ms < 60_000) return `${(ms / 1000).toFixed(1)} s`;
  const minutes = Math.floor(ms / 60_000);
  return `${minutes} min ${Math.round((ms % 60_000) / 1000)} s`;
}

export function shortHash(hash: string): string {
  return hash.length > 12 ? `${hash.slice(0, 8)}…${hash.slice(-4)}` : hash;
}

export function formatCostUsd(value: number): string {
  if (value === 0) return "$0";
  return value < 0.01 ? `$${value.toFixed(5)}` : `$${value.toFixed(3)}`;
}

export function attr(node: SpanNode, key: string): SpanAttributeValue | undefined {
  return node.attributes[key];
}

export function numberAttr(node: SpanNode, key: string): number | null {
  const value = node.attributes[key];
  return typeof value === "number" ? value : null;
}

export function textAttr(node: SpanNode, key: string): string | null {
  const value = node.attributes[key];
  return typeof value === "string" ? value : null;
}

const KIND_LABELS: Record<string, string> = {
  run: "Run",
  stage: "Stage",
  universe: "Universe",
  step: "Step",
  "option.code": "Coding",
  "option.smoke": "Smoke",
  model_call: "Model",
  sandbox_exec: "Sandbox",
  sandbox_root: "Sandbox root",
};

export function kindLabel(kind: string | null): string {
  return (kind && KIND_LABELS[kind]) || kind || "Span";
}

export function countSpans(nodes: SpanNode[]): number {
  return nodes.reduce((total, node) => total + 1 + countSpans(node.children), 0);
}
