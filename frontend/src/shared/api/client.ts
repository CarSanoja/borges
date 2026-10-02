import type {
  AgentCatalog,
  AgentDetail,
  CaseCard,
  RecordingSource,
  Health,
  Me,
  PiiSummary,
  RunCreated,
  RunRequest,
  RunSnapshot,
  TraceResponse,
  UniverseDetail,
} from "../types/contracts";

import { authHeaders } from "./apiKey";

const BASE = "/api";

export class ApiError extends Error {
  constructor(
    readonly status: number,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

function errorMessage(text: string): string {
  try {
    const body = JSON.parse(text) as { detail?: unknown };
    if (typeof body.detail === "string") return body.detail;
    if (Array.isArray(body.detail)) {
      return body.detail
        .map((item) => (item && typeof item === "object" && "msg" in item ? String(item.msg) : String(item)))
        .join("; ");
    }
  } catch {
    return text;
  }
  return text;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${BASE}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...authHeaders(), ...init?.headers },
  });
  if (!response.ok) {
    const text = await response.text().catch(() => "");
    throw new ApiError(response.status, errorMessage(text) || response.statusText);
  }
  return (await response.json()) as T;
}

export function getHealth(): Promise<Health> {
  return request<Health>("/health");
}

export function getMe(): Promise<Me> {
  return request<Me>("/me");
}

export function getAgents(): Promise<AgentCatalog> {
  return request<AgentCatalog>("/agents");
}

export function getAgent(agentId: string): Promise<AgentDetail> {
  return request<AgentDetail>(`/agents/${encodeURIComponent(agentId)}`);
}

export function getTrace(runId: string): Promise<TraceResponse> {
  return request<TraceResponse>(`/runs/${encodeURIComponent(runId)}/trace`);
}

export function getCases(): Promise<CaseCard[]> {
  return request<CaseCard[]>("/cases");
}

export function getCase(caseId: string): Promise<CaseCard> {
  return request<CaseCard>(`/cases/${encodeURIComponent(caseId)}`);
}

export interface UploadResult {
  upload_id: string;
  profile: { name: string; n_rows: number; columns: unknown[] };
  pii?: PiiSummary;
}

export async function uploadDataset(file: File): Promise<UploadResult> {
  const form = new FormData();
  form.append("file", file);
  const response = await fetch(`${BASE}/uploads`, { method: "POST", body: form, headers: authHeaders() });
  if (!response.ok) {
    const text = await response.text().catch(() => "");
    throw new ApiError(response.status, errorMessage(text) || response.statusText);
  }
  return (await response.json()) as UploadResult;
}

export function createRun(body: RunRequest): Promise<RunCreated> {
  return request<RunCreated>("/runs", { method: "POST", body: JSON.stringify(body) });
}

export function getRun(runId: string): Promise<RunSnapshot> {
  return request<RunSnapshot>(`/runs/${encodeURIComponent(runId)}`);
}

export function getUniverse(runId: string, universeId: string): Promise<UniverseDetail> {
  return request<UniverseDetail>(
    `/runs/${encodeURIComponent(runId)}/universes/${encodeURIComponent(universeId)}`,
  );
}

export function eventsUrl(runId: string, fromSeq = 0): string {
  return `${BASE}/runs/${encodeURIComponent(runId)}/events?from_seq=${fromSeq}`;
}

export function recordingUrl(caseId: string, speed = 1, source: RecordingSource | null = null): string {
  const suffix = source ? `&source=${source}` : "";
  return `${BASE}/cases/${encodeURIComponent(caseId)}/recording?speed=${speed}${suffix}`;
}
