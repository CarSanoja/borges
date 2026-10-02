import type { AgentApproval } from "../../shared/types/contracts";

export function approvalLabel(approval: AgentApproval): string {
  return approval === "unpublished" ? "unpublished change" : approval;
}

export function shortSha(sha: string | null): string {
  return sha ? sha.slice(0, 10) : "none";
}

export function formatPublished(seconds: number): string {
  return new Date(seconds * 1000).toISOString().slice(0, 16).replace("T", " ") + " UTC";
}
