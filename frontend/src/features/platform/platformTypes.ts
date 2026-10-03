export type PillarStatus = "ok" | "attention" | "off" | "error";

export interface PillarLink {
  label: string;
  path: string;
}

export interface FactProvenance {
  kind: "live" | "measured";
  source?: string;
  date?: string;
  value?: string;
  computed_at?: number | null;
}

export interface PillarProvenance {
  default: FactProvenance;
  overrides: Record<string, FactProvenance>;
}

export interface Pillar {
  id: string;
  name: string;
  brief: string;
  status: PillarStatus;
  summary: string;
  facts: Record<string, unknown>;
  code: string[];
  tests: string[];
  verify: string;
  links: PillarLink[];
  provenance?: PillarProvenance;
}

export interface PlatformStatus {
  pillars: Pillar[];
  generated_at?: number;
}
