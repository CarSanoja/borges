export function formatCount(value: number): string {
  return Math.round(value).toLocaleString("en-US");
}

export function formatTokens(value: number): string {
  const rounded = Math.round(value);
  if (rounded < 1000) return String(rounded);
  if (rounded < 1_000_000) return `${(rounded / 1000).toFixed(1)}k`;
  return `${(rounded / 1_000_000).toFixed(2)}M`;
}

export function formatCost(value: number): string {
  return `$${value.toFixed(value < 1 ? 4 : 2)}`;
}
