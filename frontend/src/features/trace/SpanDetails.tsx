import type { SpanNode } from "../../shared/types/contracts";
import { ArmorFact, isArmorRecord } from "./ArmorFact";
import { formatCostUsd, numberAttr, shortHash, textAttr } from "./spanFormat";

interface Props {
  node: SpanNode;
}

function Hash({ label, value }: { label: string; value: string | null }) {
  if (!value) return null;
  return (
    <span className="trace-fact">
      <span className="trace-fact__label">{label}</span>
      <code className="mono" title={value}>
        {shortHash(value)}
      </code>
    </span>
  );
}

function Fact({ label, value }: { label: string; value: string | number | null }) {
  if (value === null || value === "") return null;
  return (
    <span className="trace-fact">
      <span className="trace-fact__label">{label}</span>
      <span className="mono">{value}</span>
    </span>
  );
}

function ModelFacts({ node }: Props) {
  const cost = numberAttr(node, "borges.cost_usd");
  return (
    <>
      <Fact label="role" value={textAttr(node, "borges.agent.role")} />
      <Fact label="model" value={textAttr(node, "gen_ai.response.model") ?? textAttr(node, "gen_ai.request.model")} />
      <Fact label="in" value={numberAttr(node, "gen_ai.usage.input_tokens")} />
      <Fact label="out" value={numberAttr(node, "gen_ai.usage.output_tokens")} />
      <Fact label="cost" value={cost === null ? null : formatCostUsd(cost)} />
      <Fact label="cache" value={node.attributes["borges.cache.hit"] === true ? "hit" : "miss"} />
      <Hash label="prompt" value={textAttr(node, "borges.prompt.sha256")} />
      <Hash label="response" value={textAttr(node, "borges.response.sha256")} />
    </>
  );
}

function SandboxFacts({ node }: Props) {
  return (
    <>
      <Fact label="exit" value={numberAttr(node, "borges.sandbox.exit_code")} />
      <Fact label="parent" value={textAttr(node, "borges.checkpoint.parent")} />
      <Fact label="child" value={textAttr(node, "borges.checkpoint.child")} />
      <Fact label="backend" value={textAttr(node, "borges.sandbox.backend")} />
    </>
  );
}

export function SpanDetails({ node }: Props) {
  const universe = textAttr(node, "borges.universe.verdict");
  return (
    <div className="trace-facts">
      {node.kind === "model_call" && <ModelFacts node={node} />}
      {node.kind === "sandbox_exec" && <SandboxFacts node={node} />}
      {node.kind === "universe" && <Fact label="verdict" value={universe} />}
      {node.audit.filter(isArmorRecord).map((record) => (
        <ArmorFact key={record.seq} record={record} />
      ))}
      {node.audit.filter((record) => !isArmorRecord(record)).map((record) => (
        <span key={record.seq} className="trace-fact" data-decision={record.decision ?? "none"}>
          <span className="trace-fact__label">audit #{record.seq}</span>
          <code className="mono" title={record.hash}>
            {record.kind}
            {record.decision ? ` · ${record.decision}` : ""}
          </code>
        </span>
      ))}
    </div>
  );
}
