const LEADING_VERBS = /^(choose which|choose|adjust for|fit the|measure|standardise the|standardize the|handle|pick|select|use the|use)\s+/i;

function capitalise(text: string): string {
  return text.charAt(0).toUpperCase() + text.slice(1);
}

export function ringTitleCandidates(title: string): string[] {
  const stripped = capitalise(title.replace(LEADING_VERBS, "").trim());
  const first = stripped.split(/\s+/)[0] ?? stripped;
  return [...new Set([title, stripped, first])].filter((text) => text.length > 0);
}

export function fitRingTitle(title: string, room: number, maxSqueeze: number): { text: string; fits: boolean } {
  const candidates = ringTitleCandidates(title);
  const fitting = candidates.find((text) => text.length <= room * maxSqueeze);
  if (fitting) return { text: fitting, fits: true };
  const last = candidates[candidates.length - 1] ?? title;
  return { text: last, fits: false };
}
