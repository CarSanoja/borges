import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { buildSampleRun } from "../../fixtures/sampleRun";
import { RunHeader } from "./RunHeader";
import { foldEvents } from "./reducer";

const snapshot = foldEvents("r1", buildSampleRun("r1"));

describe("RunHeader mode badge", () => {
  it("labels a scripted replay on local sandboxes", () => {
    render(<RunHeader snapshot={snapshot} onHome={() => undefined} />);
    expect(screen.getByText("Scripted replay · local sandboxes")).toBeInTheDocument();
  });

  it("labels a live run and names ConTree only for the contree backend", () => {
    render(<RunHeader snapshot={{ ...snapshot, llm: "nebius", backend: "contree" }} onHome={() => undefined} />);
    expect(screen.getByText("Live on Nemotron · ConTree sandboxes")).toBeInTheDocument();
  });

  it("labels a recording made with the local Ollama model", () => {
    render(<RunHeader snapshot={{ ...snapshot, llm: "local", backend: "local" }} onHome={() => undefined} />);
    expect(screen.getByText("Nemotron 3 Nano on Ollama (local, not Token Factory) · local sandboxes")).toBeInTheDocument();
  });

  it("claims no sandbox mode before run.started", () => {
    render(<RunHeader snapshot={{ ...snapshot, llm: null, backend: null }} onHome={() => undefined} />);
    expect(screen.queryByText(/sandboxes/)).toBeNull();
  });
});

describe("RunHeader trace link", () => {
  it("links to the trace of a stored run and omits it for the mock", () => {
    const { rerender } = render(<RunHeader snapshot={snapshot} onHome={() => undefined} traceRunId="r1" />);
    expect(screen.getByRole("link", { name: "Trace" })).toHaveAttribute("href", "/run/r1/trace");
    rerender(<RunHeader snapshot={snapshot} onHome={() => undefined} />);
    expect(screen.queryByRole("link", { name: "Trace" })).toBeNull();
  });
});

describe("RunHeader provenance", () => {
  it("shows the data provenance chip in the replay header", () => {
    render(<RunHeader snapshot={snapshot} onHome={() => undefined} provenance="Real data, CC0" />);
    expect(screen.getByTestId("provenance-chip")).toHaveTextContent("Real data, CC0");
  });

  it("shows no chip when the case declares none", () => {
    render(<RunHeader snapshot={snapshot} onHome={() => undefined} />);
    expect(screen.queryByTestId("provenance-chip")).toBeNull();
  });
});

describe("RunHeader starting analysis", () => {
  it("shows the analysis the run kept as the original", () => {
    const plan = snapshot.plan ? { ...snapshot.plan, analysis: "OLS of y on x, days 7 to 14" } : null;
    render(<RunHeader snapshot={{ ...snapshot, plan }} onHome={() => undefined} />);
    expect(screen.getByText("Starting analysis, kept as the original")).toBeInTheDocument();
    expect(screen.getByText("OLS of y on x, days 7 to 14")).toBeInTheDocument();
  });

  it("has no starting analysis line for an ordinary run", () => {
    render(<RunHeader snapshot={snapshot} onHome={() => undefined} />);
    expect(screen.queryByText("Starting analysis, kept as the original")).toBeNull();
  });
});
