import { fireEvent, render, screen } from "@testing-library/react";
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

const noop = () => undefined;

function leaves() {
  return screen.getAllByTestId("garden-node").filter((n) => n.dataset.leaf === "true");
}

describe("Garden keyboard", () => {
  it("is one tab stop with a roving tabindex across the leaves", () => {
    render(<Garden snapshot={snapshot()} selectedUniverseId={null} onSelectUniverse={noop} />);
    const stops = leaves().filter((n) => n.getAttribute("tabindex") === "0");
    expect(stops).toHaveLength(1);
    expect(leaves()).toHaveLength(2);
  });

  it("moves with the arrow keys, Home and End, and Enter opens the universe", async () => {
    const onSelect = vi.fn();
    render(<Garden snapshot={snapshot()} selectedUniverseId={null} onSelectUniverse={onSelect} />);
    const [first, second] = leaves() as [HTMLElement, HTMLElement];
    first.focus();
    await userEvent.keyboard("{ArrowRight}");
    expect(second).toHaveFocus();
    expect(second).toHaveAttribute("tabindex", "0");
    expect(first).toHaveAttribute("tabindex", "-1");
    await userEvent.keyboard("{ArrowRight}");
    expect(second).toHaveFocus();
    await userEvent.keyboard("{Home}");
    expect(first).toHaveFocus();
    await userEvent.keyboard("{End}");
    expect(second).toHaveFocus();
    await userEvent.keyboard("{ArrowLeft}");
    expect(first).toHaveFocus();
    await userEvent.keyboard("{Enter}");
    expect(onSelect).toHaveBeenCalledWith(first.getAttribute("aria-label")?.startsWith("Baseline") ? "u0" : "u1");
  });

  it("makes the selected universe the tab stop", () => {
    render(<Garden snapshot={snapshot()} selectedUniverseId="u1" onSelectUniverse={noop} />);
    const stop = leaves().find((n) => n.getAttribute("tabindex") === "0");
    expect(stop?.dataset.nodeId).toBe("c2");
  });
});

describe("Garden tooltip", () => {
  it("clears when the selection closes", () => {
    const { rerender } = render(<Garden snapshot={snapshot()} selectedUniverseId={null} onSelectUniverse={noop} />);
    fireEvent.pointerMove(leaves()[0] as Element, { clientX: 10, clientY: 10 });
    expect(screen.getByTestId("garden-tooltip")).toBeInTheDocument();
    rerender(<Garden snapshot={snapshot()} selectedUniverseId="u0" onSelectUniverse={noop} />);
    expect(screen.queryByTestId("garden-tooltip")).toBeNull();
  });

  it("clears on Escape", () => {
    render(<Garden snapshot={snapshot()} selectedUniverseId={null} onSelectUniverse={noop} />);
    fireEvent.pointerMove(leaves()[0] as Element, { clientX: 10, clientY: 10 });
    expect(screen.getByTestId("garden-tooltip")).toBeInTheDocument();
    fireEvent.keyDown(document, { key: "Escape" });
    expect(screen.queryByTestId("garden-tooltip")).toBeNull();
  });
});
