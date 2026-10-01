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

  it("claims no sandbox mode before run.started", () => {
    render(<RunHeader snapshot={{ ...snapshot, llm: null, backend: null }} onHome={() => undefined} />);
    expect(screen.queryByText(/sandboxes/)).toBeNull();
  });
});
