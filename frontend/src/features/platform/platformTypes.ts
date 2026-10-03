export type PillarStatus = "ok" | "attention" | "off" | "error";

export interface PillarLink {
  label: string;
  path: string;
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
}

export interface PlatformStatus {
  pillars: Pillar[];
}
