import type { AgentApproval, EgressClass } from "../../shared/types/contracts";

export function approvalLabel(approval: AgentApproval): string {
  return approval === "unpublished" ? "unpublished change" : approval;
}

export function shortSha(sha: string | null): string {
  return sha ? sha.slice(0, 10) : "none";
}

export function formatPublished(seconds: number): string {
  return new Date(seconds * 1000).toISOString().slice(0, 16).replace("T", " ") + " UTC";
}

export function formatUsd(value: number): string {
  return `$${value.toFixed(2)}`;
}

export function egressLabel(egress: EgressClass, rows: number): string {
  if (egress === "none") return "no dataset content";
  if (egress === "profile_only") return "profile only: column names, types, summary statistics and notes";
  return `profile plus up to ${rows} redacted sample rows`;
}
