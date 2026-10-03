import type { FactProvenance, Pillar } from "./platformTypes";

export interface ProvenanceBadge {
  key: string;
  kind: "live" | "measured";
  label: string;
  detail: string;
}

export function isoDate(epochSeconds: number | null | undefined): string | null {
  if (typeof epochSeconds !== "number" || !Number.isFinite(epochSeconds)) return null;
  return new Date(epochSeconds * 1000).toISOString().slice(0, 10);
}

function badge(key: string, entry: FactProvenance): ProvenanceBadge {
  if (entry.kind === "measured") {
    const when = entry.date ? ` on ${entry.date}` : "";
    return {
      key,
      kind: "measured",
      label: `Fixed measurement${when}`,
      detail: [entry.value, entry.source].filter(Boolean).join(" - "),
    };
  }
  const when = isoDate(entry.computed_at);
  return {
    key,
    kind: "live",
    label: when ? `Live server state, cached ${when}` : "Live server state",
    detail: entry.source ?? "",
  };
}

export function provenanceBadges(pillar: Pillar): ProvenanceBadge[] {
  const provenance = pillar.provenance;
  if (!provenance) return [];
  const rows = [badge("default", provenance.default)];
  for (const [path, entry] of Object.entries(provenance.overrides ?? {})) rows.push(badge(path, entry));
  return rows;
}

export function corpusNote(pillar: Pillar): string | null {
  if (pillar.id !== "armor") return null;
  const corpus = pillar.facts.corpus as { computed_at?: number | null } | undefined;
  const override = pillar.provenance?.overrides?.["facts.corpus"];
  const date = isoDate(override?.computed_at ?? corpus?.computed_at);
  const when = date ? ` Corpus screened on ${date}.` : "";
  return `Own corpus, not independent: the authors wrote the attacks and the benign texts, so these numbers are not a third-party benchmark.${when}`;
}
