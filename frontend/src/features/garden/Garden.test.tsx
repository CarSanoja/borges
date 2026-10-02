import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import type {
  AnalysisPlan,
  AnalysisResult,
  CheckpointNode,
  RunSnapshot,
  Universe,
} from "../../shared/types/contracts";
import { Garden } from "./Garden";

const result: AnalysisResult = {
  estimate: 0.12,
  ci_low: 0.05,
  ci_high: 0.19,
  p_value: 0.004,
  n: 1000,
  metric: "lift",
  extra: {},
};

const plan: AnalysisPlan = {
  question: "q",
  estimand: "e",
  decision_rule: {
    metric: "lift",
    comparator: "gt",
    threshold: 0,
    alpha: 0.05,
    positive_label: "SHIP",
    negative_label: "DON'T SHIP",
  },
  dataset: { name: "checkout", n_rows: 5000, columns: [], sample_rows: [] },
  steps: [
    {
      id: "s1",
      title: "Outliers",
      kind: "filter",
      description: "",
      options: [
        { id: "a", label: "Keep all", rationale: "", spec: "", is_default: true, origin: "planner", source: null, defensibility: null, code: null },
        { id: "b", label: "Trim 1%", rationale: "", spec: "", is_default: false, origin: "planner", source: null, defensibility: null, code: null },
      ],
    },
  ],
};

const checkpoints: CheckpointNode[] = [
  { checkpoint_id: "root", parent_id: null, step_id: null, option_id: null, depth: 0 },
  { checkpoint_id: "c1", parent_id: "root", step_id: "s1", option_id: "a", depth: 1 },
  { checkpoint_id: "c2", parent_id: "root", step_id: "s1", option_id: "b", depth: 1 },
];

function universe(id: string, leaf: string, kind: Universe["kind"], flipped: boolean): Universe {
  return {
    id,
    choices: {},
    changed: [],
    kind,
    status: "done",
    result,
    verdict: flipped ? "DON'T SHIP" : "SHIP",
    flipped,
    checkpoints: ["root", leaf],
    traces: [],
    error: null,
    duration_s: 1,
  };
}

function snapshot(overrides: Partial<RunSnapshot> = {}): RunSnapshot {
  return {
    run_id: "r",
    status: "running",
    case_id: null,
    title: "t",
    question: "q",
    decision_rule: plan.decision_rule,
    stages: {},
    plan,
    checkpoints,
    garden: {
      baseline_id: "u0",
      universes: {
        u0: universe("u0", "c1", "baseline", false),
        u1: universe("u1", "c2", "single", true),
      },
    },
    flip: null,
    report: null,
    usage: { tokens_in: 0, tokens_out: 0, cost_usd: 0, llm_calls: 0, cached_calls: 0, checkpoints: 3, universes: 2 },
    error: null,
    last_seq: 0,
    ...overrides,
  };
}

describe("Garden", () => {
  it("renders an empty state before the root exists", () => {
    render(<Garden snapshot={snapshot({ checkpoints: [] })} selectedUniverseId={null} onSelectUniverse={() => {}} />);
    expect(screen.getByTestId("garden-empty")).toBeInTheDocument();
    expect(screen.queryAllByTestId("garden-node")).toHaveLength(0);
  });

  it("renders one node per checkpoint", () => {
    render(<Garden snapshot={snapshot()} selectedUniverseId={null} onSelectUniverse={() => {}} />);
    expect(screen.getAllByTestId("garden-node")).toHaveLength(3);
    expect(screen.getAllByTestId("garden-link")).toHaveLength(2);
    expect(screen.getAllByText("Outliers").length).toBeGreaterThan(0);
    expect(screen.getByText("5,000 rows")).toBeInTheDocument();
  });

  it("colours leaves by verdict", () => {
    render(<Garden snapshot={snapshot()} selectedUniverseId={null} onSelectUniverse={() => {}} />);
    const nodes = screen.getAllByTestId("garden-node");
    const verdictOf = (id: string) => nodes.find((n) => n.dataset.nodeId === id)?.dataset.verdict;
    expect(verdictOf("c1")).toBe("baseline");
    expect(verdictOf("c2")).toBe("flipped");
    expect(verdictOf("root")).toBe("none");
  });

  it("selects the universe when a leaf is clicked", async () => {
    const onSelect = vi.fn();
    render(<Garden snapshot={snapshot()} selectedUniverseId={null} onSelectUniverse={onSelect} />);
    const leaf = screen.getAllByTestId("garden-node").find((n) => n.dataset.nodeId === "c2");
    await userEvent.click(leaf as Element);
    expect(onSelect).toHaveBeenCalledWith("u1");
  });

  it("marks the flip path and the selected path", () => {
    const snap = snapshot();
    const flip = {
      universe_id: "u1",
      changes: [],
      baseline_result: result,
      flipped_result: result,
      baseline_verdict: "SHIP",
      flipped_verdict: "DON'T SHIP",
      reproduced: null,
      reproduce_command: null,
    };
    render(<Garden snapshot={{ ...snap, flip }} selectedUniverseId="u0" onSelectUniverse={() => {}} />);
    const roles = screen.getAllByTestId("garden-link").map((l) => l.getAttribute("data-role"));
    expect(roles).toContain("flip");
    expect(roles).toContain("selected");
  });

  it("gives leaf nodes descriptive accessible labels with step, option, verdict and estimate", () => {
    const snap = snapshot();
    const u1 = { ...snap.garden.universes.u1!, changed: ["s1"], choices: { s1: "b" } };
    const withChange = { ...snap, garden: { ...snap.garden, universes: { ...snap.garden.universes, u1 } } };
    render(<Garden snapshot={withChange} selectedUniverseId={null} onSelectUniverse={() => {}} />);
    const label = screen.getByRole("button", { name: /^Universe u1/ });
    expect(label).toHaveAccessibleName("Universe u1, changes Outliers: Trim 1%, verdict DON'T SHIP, estimate 0.120, flips the verdict");
    expect(screen.getByRole("button", { name: /^Baseline universe, default choices, verdict SHIP, estimate 0.120$/ })).toBeInTheDocument();
  });
});
