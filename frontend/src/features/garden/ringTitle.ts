const LEADING_VERBS = /^(choose which|choose|adjust for|fit the|measure|standardise the|standardize the|handle|pick|select|use the|use)\s+/i;

function capitalise(text: string): string {
  return text.charAt(0).toUpperCase() + text.slice(1);
}

export function ringTitleCandidates(title: string): string[] {
  const stripped = capitalise(title.replace(LEADING_VERBS, "").trim());
  const first = stripped.split(/\s+/)[0] ?? stripped;
  return [...new Set([title, stripped, first])].filter((text) => text.length > 0);
}

export const GLYPH_WIDTH = 8.4;
export const MAX_SQUEEZE = 1.08;

export interface FittedLabel {
  text: string;
  textLength?: number;
}

export function fitRingLabel(title: string, arc: number): FittedLabel {
  const room = Math.floor(arc / GLYPH_WIDTH);
  const picked = fitRingTitle(title, room, MAX_SQUEEZE);
  if (!picked.fits) return { text: `${picked.text.slice(0, Math.max(room - 1, 3)).trimEnd()}…` };
  if (picked.text.length <= room) return { text: picked.text };
  return { text: picked.text, textLength: arc * 0.96 };
}

export function fitRingTitle(title: string, room: number, maxSqueeze: number): { text: string; fits: boolean } {
  const candidates = ringTitleCandidates(title);
  const fitting = candidates.find((text) => text.length <= room * maxSqueeze);
  if (fitting) return { text: fitting, fits: true };
  const last = candidates[candidates.length - 1] ?? title;
  return { text: last, fits: false };
}
