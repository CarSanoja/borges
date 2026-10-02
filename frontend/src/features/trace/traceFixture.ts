import type { AuditChainStatus, SpanNode, TraceResponse } from "../../shared/types/contracts";

export const PROMPT_HASH = "a".repeat(64);
export const RESPONSE_HASH = "b".repeat(64);

function node(partial: Partial<SpanNode> & Pick<SpanNode, "span_id" | "name" | "kind">): SpanNode {
  return {
    parent_span_id: null,
    status: "UNSET",
    start_ns: 1,
    end_ns: 2,
    duration_ms: 12.4,
    attributes: {},
    audit: [],
    children: [],
    ...partial,
  };
}

export const CHAIN_OK: AuditChainStatus = {
  path: "runs/r1/audit.jsonl",
  exists: true,
  ok: true,
  records: 9,
  head_hash: "c".repeat(64),
  broken_seq: null,
  broken_line: null,
  reason: null,
};

export function sampleTrace(chain: AuditChainStatus | null = CHAIN_OK): TraceResponse {
  const model = node({
    span_id: "m1",
    name: "chat nvidia/nemotron",
    kind: "model_call",
    duration_ms: 1840,
    attributes: {
      "gen_ai.request.model": "nvidia/nemotron",
      "gen_ai.response.model": "nvidia/nemotron",
      "gen_ai.usage.input_tokens": 1200,
      "gen_ai.usage.output_tokens": 340,
      "borges.agent.role": "planner",
      "borges.cost_usd": 0.0009,
      "borges.cache.hit": false,
      "borges.prompt.sha256": PROMPT_HASH,
      "borges.response.sha256": RESPONSE_HASH,
    },
    audit: [
      {
        v: 1,
        seq: 4,
        ts: "2026-10-02T16:00:00Z",
        kind: "model.call",
        run_id: "r1",
        trace_id: "t",
        span_id: "m1",
        principal: "agent:planner",
        decision: null,
        reason: null,
        data: {},
        prev_hash: "d".repeat(64),
        hash: "e".repeat(64),
      },
    ],
  });
  const sandbox = node({
    span_id: "x1",
    name: "sandbox.exec",
    kind: "sandbox_exec",
    status: "ERROR",
    attributes: { "borges.sandbox.exit_code": 1, "borges.checkpoint.parent": "c0", "borges.checkpoint.child": "c1" },
  });
  const universe = node({ span_id: "u1", name: "universe u_1", kind: "universe", children: [sandbox] });
  const stage = node({ span_id: "s1", name: "stage planning", kind: "stage", children: [model, universe] });
  const run = node({ span_id: "r1", name: "run r1", kind: "run", children: [stage] });
  return {
    run_id: "r1",
    trace_id: "f".repeat(32),
    span_count: 5,
    spans_by_kind: { run: 1, stage: 1, model_call: 1, universe: 1, sandbox_exec: 1 },
    roots: [run],
    unlinked_audit: [],
    audit_chain: chain,
    reason: null,
  };
}
