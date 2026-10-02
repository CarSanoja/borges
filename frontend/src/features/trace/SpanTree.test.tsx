import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { SpanTree } from "./SpanTree";
import { PROMPT_HASH, sampleTrace } from "./traceFixture";

describe("SpanTree", () => {
  it("shows model, tokens, cost, latency and hashes of a model call", () => {
    render(<SpanTree roots={sampleTrace().roots} />);
    expect(screen.getByText("chat nvidia/nemotron")).toBeInTheDocument();
    expect(screen.getByText("1.8 s")).toBeInTheDocument();
    expect(screen.getByText("1200")).toBeInTheDocument();
    expect(screen.getByText("340")).toBeInTheDocument();
    expect(screen.getByText("$0.00090")).toBeInTheDocument();
    expect(screen.getByText("planner")).toBeInTheDocument();
    expect(screen.getByTitle(PROMPT_HASH)).toHaveTextContent("aaaaaaaa…aaaa");
    expect(screen.getByText("model.call")).toBeInTheDocument();
  });

  it("collapses and expands a node", () => {
    render(<SpanTree roots={sampleTrace().roots} openDepth={1} />);
    expect(screen.queryByText("chat nvidia/nemotron")).toBeNull();
    fireEvent.click(screen.getByRole("button", { name: "Expand stage planning" }));
    expect(screen.getByText("chat nvidia/nemotron")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Collapse stage planning" }));
    expect(screen.queryByText("chat nvidia/nemotron")).toBeNull();
  });

  it("flags failed spans and shows sandbox checkpoints", () => {
    render(<SpanTree roots={sampleTrace().roots} openDepth={5} />);
    expect(screen.getByText("error")).toBeInTheDocument();
    expect(screen.getByText("c0")).toBeInTheDocument();
    expect(screen.getByText("c1")).toBeInTheDocument();
  });
});
